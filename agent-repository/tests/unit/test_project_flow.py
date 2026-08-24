from pathlib import Path

import pytest

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.application.ports.tool_executor import ToolExecutionResult
from agent_platform.control_plane.spoc_compiler import CompileSpocService
from agent_platform.domain.run import RunStatus
from agent_platform.execution_plane.project_flow import (
    CancellationToken,
    FlowRunOptions,
    ProjectExecutionFlow,
)
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry

TEST_CASES = [
    {"id": "AC-1", "executor": {"tool_id": "test.pytest", "tool_version": "1.0.0"}},
    {"id": "AC-2", "executor": {"tool_id": "test.pytest", "tool_version": "1.0.0"}},
]


@pytest.fixture
def manifest(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    id_generator = SequentialIdGenerator()
    policy = LocalDevPolicyDecisionPoint(decision_id_generator=id_generator)
    compiler = CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=policy,
        clock=FixedClock(),
        id_generator=id_generator,
    )
    spoc = load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter
    return compiler.compile(spoc, project_id="PRJ-001")


def _make_flow(tool_results: dict[str, ToolExecutionResult]):
    return ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=InMemoryEventLedger(),
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        tool_executor=FakeToolExecutor(tool_results),
        clock=FixedClock(),
        id_generator=SequentialIdGenerator(),
    )


def test_end_to_end_vertical_slice_all_pass(manifest, tmp_path):
    flow = _make_flow(
        {
            "AC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            "AC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
        }
    )
    options = FlowRunOptions(
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        human_plan_approved=True,
        human_acceptance_approved=True,
        summary_output_path=tmp_path / "summary.md",
    )

    state = flow.start(manifest, options)

    assert state.status == RunStatus.CLOSED
    assert (tmp_path / "summary.md").exists()
    assert "AC-1" in (tmp_path / "summary.md").read_text()

    # Every flow step emitted at least one event (M3.7 coverage requirement).
    events = flow.event_ledger.events_for_run(manifest.run_id)
    step_ids_with_events = {e.step_id for e in events if e.step_id}
    for expected_step in state.completed_steps:
        assert expected_step in step_ids_with_events


def test_human_plan_approval_pauses_when_not_approved(manifest):
    flow = _make_flow(
        {
            "AC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            "AC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
        }
    )
    options = FlowRunOptions(
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        human_plan_approved=False,
    )

    state = flow.start(manifest, options)
    assert state.status == RunStatus.WAITING_FOR_HUMAN
    assert "execute_bounded_crews" not in state.completed_steps


def test_qa_rework_loop_then_success_on_second_attempt(schema_dir, fixtures_dir):
    # Uses one shared id_generator across compilation and flow execution so
    # attempt ids are guaranteed monotonically unique, as they would be with
    # a single platform-wide IdGenerator in production.
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    shared_id_generator = SequentialIdGenerator()
    policy = LocalDevPolicyDecisionPoint(decision_id_generator=shared_id_generator)
    compiler = CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=policy,
        clock=FixedClock(),
        id_generator=shared_id_generator,
    )
    spoc = load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter
    local_manifest = compiler.compile(spoc, project_id="PRJ-001")

    flow = ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=InMemoryEventLedger(),
        approval_gateway=InMemoryApprovalGateway(),
        policy=policy,
        tool_executor=FakeToolExecutor(
            {
                "AC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
                "AC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=1, passed=False, evidence={}),
            }
        ),
        clock=FixedClock(),
        id_generator=shared_id_generator,
    )
    options = FlowRunOptions(
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        max_qa_attempts=2,
    )

    first_attempt_state = flow.start(local_manifest, options)
    assert first_attempt_state.status == RunStatus.REJECTED
    assert first_attempt_state.qa_rework_count == 1

    # Second attempt: corrected artifact now passes both test cases.
    flow.tool_executor = FakeToolExecutor(
        {
            "AC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            "AC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
        }
    )
    second_attempt_state = flow.start_new_attempt(first_attempt_state)
    final_state = flow.resume(
        second_attempt_state.manifest.run_id, second_attempt_state.manifest.attempt_id, options
    )

    assert final_state.status == RunStatus.CLOSED
    assert final_state.manifest.attempt_id != first_attempt_state.manifest.attempt_id
    assert final_state.manifest.run_id == first_attempt_state.manifest.run_id  # same run, new attempt


def test_exhausted_retries_reach_dead_letter(manifest):
    flow = _make_flow(
        {
            "AC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            "AC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=1, passed=False, evidence={}),
        }
    )
    options = FlowRunOptions(
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        max_qa_attempts=1,
    )

    state = flow.start(manifest, options)
    assert state.status == RunStatus.DEAD_LETTER
    events = flow.event_ledger.events_for_run(manifest.run_id)
    assert any(e.event_type == "human_escalation_required" for e in events)


def test_resume_after_interruption_does_not_reexecute_completed_steps(manifest):
    run_state_store = InMemoryRunStateStore()
    event_ledger = InMemoryEventLedger()
    flow = ProjectExecutionFlow(
        run_state_store=run_state_store,
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
        originating_agent_id="architecture_writer", qa_agent_id="qa_evaluator", test_cases=TEST_CASES
    )

    token = CancellationToken()
    token.cancel()  # simulate an interruption before any step executes
    state = flow.start(manifest, options, cancellation_token=token)
    assert state.status == RunStatus.CANCELLED
    assert state.completed_steps == []

    # "Restart" with a fresh token: resume from the persisted (empty) state.
    resumed_state = flow.resume(manifest.run_id, manifest.attempt_id, options, cancellation_token=None)
    assert resumed_state.status == RunStatus.CLOSED
    assert "load_run_manifest" in resumed_state.completed_steps
