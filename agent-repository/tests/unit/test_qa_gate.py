import pytest

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.application.ports.tool_executor import ToolExecutionResult
from agent_platform.execution_plane.qa_gate import SelfApprovalError, qa_validation_against_test_cases

TEST_CASES = [
    {"id": "TC-1", "executor": {"tool_id": "test.pytest", "tool_version": "1.0.0"}},
    {"id": "TC-2", "executor": {"tool_id": "test.pytest", "tool_version": "1.0.0"}},
]


def _make_ledger_and_ids():
    return InMemoryEventLedger(), SequentialIdGenerator(), FixedClock()


def test_all_passing_test_cases_advance_to_specialist_review():
    ledger, ids, clock = _make_ledger_and_ids()
    executor = FakeToolExecutor(
        {
            "TC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            "TC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
        }
    )

    outcome = qa_validation_against_test_cases(
        run_id="run_1",
        attempt_id="attempt_1",
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        tool_executor=executor,
        event_ledger=ledger,
        clock=clock,
        id_generator=ids,
        qa_rework_count=0,
        max_attempts=2,
    )

    assert outcome.all_passed is True
    assert outcome.next_state == "specialist_review"
    events = ledger.events_for_run("run_1")
    assert any(e.event_type == "qa_review_passed" for e in events)
    assert sum(1 for e in events if e.event_type == "test_case_executed") == 2


def test_one_failing_test_case_returns_to_originating_agent():
    ledger, ids, clock = _make_ledger_and_ids()
    executor = FakeToolExecutor(
        {
            "TC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
            "TC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=1, passed=False, evidence={"log": "assertion failed"}),
        }
    )

    outcome = qa_validation_against_test_cases(
        run_id="run_1",
        attempt_id="attempt_1",
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        tool_executor=executor,
        event_ledger=ledger,
        clock=clock,
        id_generator=ids,
        qa_rework_count=0,
        max_attempts=2,
    )

    assert outcome.all_passed is False
    assert outcome.next_state == "return_to_originating_agent"
    assert outcome.qa_rework_count == 1
    assert outcome.failing_test_case_ids == ["TC-2"]

    events = ledger.events_for_run("run_1")
    rejection_events = [e for e in events if e.event_type == "qa_review_rejected"]
    assert len(rejection_events) == 1
    assert rejection_events[0].payload["target_agent"] == "architecture_writer"


def test_exhausting_retries_transitions_to_dead_letter():
    ledger, ids, clock = _make_ledger_and_ids()
    executor = FakeToolExecutor(
        {
            "TC-1": ToolExecutionResult(tool_id="test.pytest", exit_code=1, passed=False, evidence={}),
            "TC-2": ToolExecutionResult(tool_id="test.pytest", exit_code=0, passed=True, evidence={}),
        }
    )

    outcome = qa_validation_against_test_cases(
        run_id="run_1",
        attempt_id="attempt_2",
        originating_agent_id="architecture_writer",
        qa_agent_id="qa_evaluator",
        test_cases=TEST_CASES,
        tool_executor=executor,
        event_ledger=ledger,
        clock=clock,
        id_generator=ids,
        qa_rework_count=1,  # already had one rework attempt
        max_attempts=2,
    )

    assert outcome.next_state == "dead_letter"
    events = ledger.events_for_run("run_1")
    assert any(e.event_type == "human_escalation_required" or e.event_type == "qa_review_rejected" for e in events)


def test_self_approval_is_rejected_by_hard_assertion():
    ledger, ids, clock = _make_ledger_and_ids()
    executor = FakeToolExecutor({})

    with pytest.raises(SelfApprovalError):
        qa_validation_against_test_cases(
            run_id="run_1",
            attempt_id="attempt_1",
            originating_agent_id="qa_evaluator",
            qa_agent_id="qa_evaluator",
            test_cases=TEST_CASES,
            tool_executor=executor,
            event_ledger=ledger,
            clock=clock,
            id_generator=ids,
            qa_rework_count=0,
            max_attempts=2,
        )
