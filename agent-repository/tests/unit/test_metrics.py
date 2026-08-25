"""Metrics registry, catalog, dashboard/alert config, and instrumentation
tests (plan milestone M8.1 Definition of done)."""

import json
from pathlib import Path

import pytest
import yaml

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.control_plane.budget_enforcer import BudgetEnforcer, BudgetLimitExceededError
from agent_platform.control_plane.policy_engine import HARD_DENY_ACTIONS, PolicyEngine
from agent_platform.domain.run import CostState, RunManifest, RunStatus
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow
from agent_platform.telemetry.metrics import (
    METRIC_FAMILIES,
    MetricDefinition,
    MetricKind,
    MetricsRegistry,
    safety_relevant_metric_names,
    standard_platform_metrics,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "ops" / "dashboards" / "platform.json"
ALERTS_PATH = REPO_ROOT / "ops" / "alerts" / "platform_alerts.yml"


# -- registry semantics -----------------------------------------------------

def test_counter_increments():
    registry = MetricsRegistry()
    registry.inc("requests_total", 1, labels={"route": "/health"})
    registry.inc("requests_total", 2, labels={"route": "/health"})
    metric = registry.get("requests_total", MetricKind.COUNTER)
    assert metric.samples[0].value == 3
    assert metric.samples[0].count == 2


def test_gauge_last_write_wins():
    registry = MetricsRegistry()
    registry.set_gauge("temperature", 10.0)
    registry.set_gauge("temperature", 42.0)
    assert registry.get("temperature", MetricKind.GAUGE).samples[0].value == 42.0


def test_histogram_accumulates_sum_count_and_buckets():
    registry = MetricsRegistry()
    registry.observe("latency", 0.2)
    registry.observe("latency", 2.5)
    metric = registry.get("latency", MetricKind.HISTOGRAM)
    assert metric.samples[0].count == 2
    assert metric.samples[0].sum == 2.7
    assert metric.samples[0].buckets[0.5] == 1  # only 0.2 <= 0.5
    assert metric.samples[0].buckets[5.0] == 2  # both <= 5.0


def test_prometheus_rendering_is_deterministic_and_scrapeable():
    registry = MetricsRegistry()
    registry.inc("run_completion_total", labels={"status": "closed"})
    text = registry.render_prometheus()
    assert 'run_completion_total{status="closed"} 1' in text
    assert text.endswith("\n")


def test_json_rendering_round_trips():
    registry = standard_platform_metrics()
    registry.inc("policy_denial_total", labels={"action": "write_to_production"})
    payload = json.loads(registry.render_json())
    names = {entry["name"] for entry in payload}
    assert "policy_denial_total" in names
    assert len(payload) >= 18  # all six families


# -- catalog: masterplan section 16.4 coverage -------------------------------

def test_every_metric_family_has_definitions():
    assert set(METRIC_FAMILIES) == {
        "reliability",
        "quality",
        "operations",
        "economics",
        "governance",
        "project_value",
    }
    for family, definitions in METRIC_FAMILIES.items():
        assert definitions, f"family {family} has no metrics"


def test_safety_relevant_metrics_present():
    assert safety_relevant_metric_names() == {
        "run_dead_letter_total",
        "budget_exhausted_total",
        "policy_denial_total",
    }


def test_standard_registry_registers_every_definition():
    registry = standard_platform_metrics()
    expected = {d.name for defs in METRIC_FAMILIES.values() for d in defs}
    collected = {m.name for m in registry.collect()}
    assert expected == collected


# -- dashboard and alert config ----------------------------------------------

def test_dashboard_has_a_panel_per_family():
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    panels = dashboard["panels"]
    assert len(panels) >= 6
    for panel in panels:
        assert panel.get("targets"), f"panel '{panel.get('title')}' has no targets"


def test_alerts_cover_safety_relevant_metrics():
    alerts = yaml.safe_load(ALERTS_PATH.read_text(encoding="utf-8"))
    alert_names = {rule["alert"] for group in alerts["groups"] for rule in group["rules"]}
    # Budget, dead-letter, and policy denial must each have an alert.
    assert {"BudgetExhausted", "DeadLetterRateSpike", "PolicyDenialSpike"} <= alert_names
    # Approval-lead-time SLA alert required by the DoD as well.
    assert "ApprovalLeadTimeSLA" in alert_names


# -- instrumentation -----------------------------------------------------------

def _manifest(run_id: str = "run_1") -> RunManifest:
    return RunManifest(
        project_id="PRJ-001",
        spoc_id="SPOC-1",
        spoc_version="sha256:abc",
        execution_key="execkey_1",
        run_id=run_id,
        attempt_id="attempt_1",
        correlation_id="corr_1",
        workflow_id="wf",
        workflow_version="1.0.0",
        approval_required=True,
    )


def test_flow_records_completion_and_duration_metrics():
    metrics = MetricsRegistry([MetricDefinition("run_completion_total", "", MetricKind.COUNTER, "reliability"),
                               MetricDefinition("run_duration_seconds", "", MetricKind.HISTOGRAM, "operations"),
                               MetricDefinition("run_dead_letter_total", "", MetricKind.COUNTER, "reliability")])
    flow = ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=InMemoryEventLedger(),
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        tool_executor=FakeToolExecutor({}),
        clock=FixedClock(),
        id_generator=SequentialIdGenerator(),
        metrics=metrics,
    )
    state = flow.start(_manifest(), FlowRunOptions(originating_agent_id="a", qa_agent_id="q", test_cases=[]))
    assert state.status == RunStatus.CLOSED
    completion = metrics.get("run_completion_total", MetricKind.COUNTER)
    assert any(s.labels == (("status", "closed"), ("workflow", "wf")) for s in completion.samples)
    duration = metrics.get("run_duration_seconds", MetricKind.HISTOGRAM)
    assert duration.samples[0].count == 1


def test_policy_engine_records_denials():
    metrics = MetricsRegistry([MetricDefinition("policy_denial_total", "", MetricKind.COUNTER, "governance")])
    policy = PolicyEngine(id_generator=SequentialIdGenerator(), metrics=metrics)
    decision = policy.evaluate(action="write_to_production", context={})
    assert decision.allowed is False
    assert metrics.get("policy_denial_total", MetricKind.COUNTER).samples[0].value == 1


def test_budget_enforcer_records_exhaustion():
    metrics = MetricsRegistry([MetricDefinition("budget_exhausted_total", "", MetricKind.COUNTER, "economics")])
    enforcer = BudgetEnforcer(metrics=metrics)
    with pytest.raises(BudgetLimitExceededError):
        enforcer.enforce(
            run_id="run-1",
            attempt_id="attempt-1",
            cost_state=CostState(spent_usd=4.0),
            additional_cost_usd=2.0,
            max_total_cost_usd=5.0,
        )
    assert metrics.get("budget_exhausted_total", MetricKind.COUNTER).samples[0].value == 1
