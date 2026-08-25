"""Failure-injection integration tests (masterplan section 20.2, plan
milestone M8.3).

Covers the resilience scenarios that exercise the whole pipeline rather
than a single unit: tool timeout followed by retry then success, and
duplicate execution of the same manifest returning the existing run
without re-running side effects.
"""

import pytest

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.adapters.tool_executor import RetryingToolExecutor, ToolTimeoutError
from agent_platform.application.ports.tool_executor import ToolExecutionResult
from agent_platform.domain.run import RunManifest, RunStatus
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow


class FlakyFakeToolExecutor:
    """Fails with a timeout for the first N calls, then delegates to a
    preconfigured result."""

    def __init__(self, results_by_test_case: dict[str, ToolExecutionResult], timeouts: int):
        self._results = results_by_test_case
        self._timeouts = timeouts
        self.calls = 0

    def execute(self, *, tool_id: str, tool_version: str, input_payload: dict) -> ToolExecutionResult:
        self.calls += 1
        if self.calls <= self._timeouts:
            raise ToolTimeoutError(f"tool {tool_id} timed out (call {self.calls})")
        return self._results[input_payload["test_case_id"]]


def _manifest(run_id: str = "run-1") -> RunManifest:
    return RunManifest(
        project_id="PRJ-001",
        spoc_id="SPOC-1",
        spoc_version="sha256:abc",
        execution_key="execkey-1",
        run_id=run_id,
        attempt_id="attempt-1",
        correlation_id="corr-1",
        workflow_id="wf",
        workflow_version="1.0.0",
        approval_required=True,
    )


def _flow(tool_executor) -> ProjectExecutionFlow:
    ids = SequentialIdGenerator()
    return ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=InMemoryEventLedger(),
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=ids),
        tool_executor=tool_executor,
        clock=FixedClock(),
        id_generator=ids,
    )


def test_tool_timeout_then_retry_then_success_reaches_closed():
    inner = FlakyFakeToolExecutor(
        {"TC-1": ToolExecutionResult(tool_id="t", exit_code=0, passed=True, evidence={"ok": True})},
        timeouts=2,
    )
    flow = _flow(RetryingToolExecutor(inner, max_attempts=3, sleep_fn=lambda _: None))
    options = FlowRunOptions(
        originating_agent_id="architect",
        qa_agent_id="qa",
        test_cases=[{"id": "TC-1", "executor": {"tool_id": "qa.test_runner", "tool_version": "1.0.0"}}],
    )

    state = flow.start(_manifest(), options)

    assert state.status == RunStatus.CLOSED
    assert inner.calls == 3  # two timeouts, one success


def test_duplicate_execution_returns_existing_run_without_rerunning_tool():
    inner = FlakyFakeToolExecutor(
        {"TC-1": ToolExecutionResult(tool_id="t", exit_code=0, passed=True, evidence={"ok": True})},
        timeouts=0,
    )
    flow = _flow(inner)
    options = FlowRunOptions(
        originating_agent_id="architect",
        qa_agent_id="qa",
        test_cases=[{"id": "TC-1", "executor": {"tool_id": "qa.test_runner", "tool_version": "1.0.0"}}],
    )
    manifest = _manifest("run-dup")

    first = flow.start(manifest, options)
    calls_after_first = inner.calls
    second = flow.start(manifest, options)  # same manifest -> existing run

    assert first.manifest.run_id == second.manifest.run_id
    assert first.status == RunStatus.CLOSED
    assert second.status == RunStatus.CLOSED
    assert inner.calls == calls_after_first  # no side-effect re-execution
