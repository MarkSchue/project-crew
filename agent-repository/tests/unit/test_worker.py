"""Worker and lease-recovery tests (plan milestone M6.3 Definition of
done)."""

import pytest

from agent_platform.adapters.clock_and_ids import SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.domain.run import ProjectRunState, RunManifest, RunStatus
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow
from agent_platform.execution_plane.worker import InMemoryLeaseStore, LeaseUnavailableError, Worker


class MutableClock:
    def __init__(self, start: str = "2026-08-24T09:00:00Z"):
        self._now = start

    def now_iso(self) -> str:
        return self._now

    def advance_seconds(self, seconds: int) -> None:
        from datetime import datetime, timedelta

        dt = datetime.fromisoformat(self._now.replace("Z", "+00:00"))
        self._now = (dt + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


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
        approval_required=True,
    )


def _flow(run_state_store, event_ledger):
    return ProjectExecutionFlow(
        run_state_store=run_state_store,
        event_ledger=event_ledger,
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        tool_executor=FakeToolExecutor({}),
        clock=MutableClock(),
        id_generator=SequentialIdGenerator(),
    )


def test_worker_runs_and_releases_lease():
    run_state_store = InMemoryRunStateStore()
    event_ledger = InMemoryEventLedger()
    worker = Worker(
        flow=_flow(run_state_store, event_ledger),
        lease_store=InMemoryLeaseStore(),
        clock=MutableClock(),
        owner="worker-1",
    )
    options = FlowRunOptions(originating_agent_id="a", qa_agent_id="q", test_cases=[])

    state = worker.run_once(_manifest(), options)
    assert state.status == RunStatus.CLOSED
    # Lease released after the run.
    assert worker.lease_store.get("run_1") is None


def test_second_worker_cannot_steal_active_lease():
    flow = _flow(InMemoryRunStateStore(), InMemoryEventLedger())
    lease_store = InMemoryLeaseStore()
    clock = MutableClock()
    lease_store.acquire("run_1", "worker-1", 30, clock.now_iso())

    worker2 = Worker(flow=flow, lease_store=lease_store, clock=clock, owner="worker-2")
    with pytest.raises(LeaseUnavailableError):
        worker2.run_once(_manifest(), FlowRunOptions(originating_agent_id="a", qa_agent_id="q", test_cases=[]))


def test_expired_lease_is_recovered_with_reconciliation():
    run_state_store = InMemoryRunStateStore()
    event_ledger = InMemoryEventLedger()
    clock = MutableClock()
    lease_store = InMemoryLeaseStore()

    # Simulate a crashed worker: prior partial state persisted, and its
    # lease has expired.
    partial = ProjectRunState(manifest=_manifest(), status=RunStatus.RUNNING)
    partial.record_step_complete("load_run_manifest")
    partial.record_step_complete("preflight_policy_check")
    run_state_store.save("run_1", "attempt_1", partial)
    lease_store.acquire("run_1", "worker-1", 10, "2026-08-24T09:00:00Z")
    clock.advance_seconds(11)  # lease now expired

    worker2 = Worker(
        flow=_flow(run_state_store, event_ledger),
        lease_store=lease_store,
        clock=clock,
        owner="worker-2",
    )
    options = FlowRunOptions(originating_agent_id="a", qa_agent_id="q", test_cases=[])

    state = worker2.run_once(_manifest(), options)

    assert state.status == RunStatus.CLOSED
    # Reconciliation recorded the prior side effects.
    reconciliation = [e for e in event_ledger.events_for_run("run_1") if e.event_type == "lease_reconciliation"]
    assert len(reconciliation) == 1
    assert set(reconciliation[0].payload["prior_completed_steps"]) >= {"load_run_manifest", "preflight_policy_check"}
    # The prior steps were not re-executed (they remain in completed_steps).
    assert "load_run_manifest" in state.completed_steps
