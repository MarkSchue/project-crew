"""SQLite persistence adapter tests (plan milestone M6.2)."""

import pytest

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.sqlite import SqliteEventLedger, SqliteRunStateStore
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import ProjectRunState, RunManifest, RunStatus


def _manifest(run_id: str = "run_1", attempt_id: str = "attempt_1") -> RunManifest:
    return RunManifest(
        project_id="PRJ-001",
        spoc_id="SPOC-1",
        spoc_version="sha256:abc",
        execution_key="execkey_1",
        run_id=run_id,
        attempt_id=attempt_id,
        correlation_id="corr_1",
        workflow_id="wf",
        workflow_version="1.0.0",
    )


def test_run_state_roundtrip_and_resume(tmp_path):
    store = SqliteRunStateStore(tmp_path / "state.db")
    state = ProjectRunState(manifest=_manifest(), status=RunStatus.RUNNING)
    state.record_step_complete("load_run_manifest")

    store.save("run_1", "attempt_1", state)
    loaded = store.load("run_1", "attempt_1")

    assert loaded.status == RunStatus.RUNNING
    assert loaded.completed_steps == ["load_run_manifest"]
    assert store.latest_attempt_id("run_1") == "attempt_1"
    assert store.list_run_ids() == ["run_1"]


def test_event_ledger_append_and_read(tmp_path):
    ledger = SqliteEventLedger(tmp_path / "events.db")
    event = RunEvent(
        event_id="evt_1",
        run_id="run_1",
        attempt_id="attempt_1",
        aggregate_id="run_1",
        event_type="test_event",
        timestamp="2026-08-24T09:00:00Z",
        actor=Actor(type="system", id="test"),
    )
    ledger.append(event)
    # Append-only at the port level: appending the same event_id is a no-op.
    ledger.append(event)

    events = ledger.events_for_run("run_1")
    assert len(events) == 1
    assert events[0].event_id == "evt_1"


def test_flow_vertical_slice_runs_against_sqlite(schema_dir, fixtures_dir, tmp_path):
    """The Phase 3 vertical-slice flow runs unchanged against the SQLite
    stores, proving the persistence layer is swappable (M6.2 DoD)."""
    from agent_platform.adapters.approval import InMemoryApprovalGateway
    from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
    from agent_platform.adapters.tool_executor import FakeToolExecutor
    from agent_platform.application.ports.tool_executor import ToolExecutionResult
    from agent_platform.control_plane.spoc_compiler import CompileSpocService
    from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow
    from agent_platform.registries.agent_registry import load_agent_registry
    from agent_platform.registries.capability_registry import load_capability_registry
    from agent_platform.registries.workflow_registry import load_workflow_registry
    from agent_platform.schemas.canonicalize import load_okf_file
    from agent_platform.schemas.okf_linter import SchemaRegistry

    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    ids = SequentialIdGenerator()
    compiler = CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=ids),
        clock=FixedClock(),
        id_generator=ids,
    )
    spoc = load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter
    manifest = compiler.compile(spoc, project_id="PRJ-001")

    event_ledger = SqliteEventLedger(tmp_path / "events.db")
    flow = ProjectExecutionFlow(
        run_state_store=SqliteRunStateStore(tmp_path / "state.db"),
        event_ledger=event_ledger,
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        tool_executor=FakeToolExecutor(
            {
                "AC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
                "AC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            }
        ),
        clock=FixedClock(),
        id_generator=SequentialIdGenerator(),
    )
    options = FlowRunOptions(
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=[{"id": "AC-1"}, {"id": "AC-2"}],
    )
    state = flow.start(manifest, options)

    assert state.status == RunStatus.CLOSED
    assert event_ledger.events_for_run(manifest.run_id), "events should be persisted in SQLite"
