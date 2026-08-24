"""QA gate and rework loop (masterplan section 13.5, plan section 21,
ADR-020). Plan milestone M3.8.

Deterministic test execution happens through the injected ``ToolExecutor``
port; this module only interprets the resulting evidence and decides
pass/fail/rework/dead_letter. It never executes a test itself.

Hard rule (M3.8 DoD): the QA agent must not be the same actor as the
originating agent. This is enforced as a hard assertion, not a
convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.application.ports.tool_executor import ToolExecutor
from agent_platform.domain.events import Actor, RunEvent


class SelfApprovalError(AssertionError):
    """Raised when the QA agent and the originating agent are the same
    actor (masterplan section 13.5, M3.8 hard check)."""


@dataclass(frozen=True)
class TestResult:
    test_case_id: str
    passed: bool
    evidence: dict


@dataclass
class QaOutcome:
    test_results: list[TestResult]
    all_passed: bool
    next_state: str  # "specialist_review" | "return_to_originating_agent" | "dead_letter"
    qa_rework_count: int
    failing_test_case_ids: list[str] = field(default_factory=list)


def qa_validation_against_test_cases(
    *,
    run_id: str,
    attempt_id: str,
    originating_agent_id: str,
    qa_agent_id: str,
    test_cases: list[dict],
    tool_executor: ToolExecutor,
    event_ledger: EventLedger,
    clock: Clock,
    id_generator: IdGenerator,
    qa_rework_count: int,
    max_attempts: int,
) -> QaOutcome:
    if originating_agent_id == qa_agent_id:
        raise SelfApprovalError(
            f"QA agent '{qa_agent_id}' must not be the originating agent for run '{run_id}'"
        )

    results: list[TestResult] = []
    for test_case in test_cases:
        executor = test_case.get("executor", {})
        outcome = tool_executor.execute(
            tool_id=executor.get("tool_id", "test.unknown"),
            tool_version=executor.get("tool_version", "0.0.0"),
            input_payload={"test_case_id": test_case["id"]},
        )
        result = TestResult(test_case_id=test_case["id"], passed=outcome.passed, evidence=outcome.evidence)
        results.append(result)

        event_ledger.append(
            RunEvent(
                event_id=id_generator.new_id("evt"),
                run_id=run_id,
                attempt_id=attempt_id,
                step_id="qa_validation_against_test_cases",
                aggregate_id=run_id,
                event_type="test_case_executed",
                timestamp=clock.now_iso(),
                actor=Actor(type="agent", id=qa_agent_id),
                payload={"test_case_id": test_case["id"], "passed": result.passed},
            )
        )

    all_passed = all(r.passed for r in results)
    failing_ids = [r.test_case_id for r in results if not r.passed]

    if all_passed:
        event_ledger.append(
            RunEvent(
                event_id=id_generator.new_id("evt"),
                run_id=run_id,
                attempt_id=attempt_id,
                step_id="qa_validation_against_test_cases",
                aggregate_id=run_id,
                event_type="qa_review_passed",
                timestamp=clock.now_iso(),
                actor=Actor(type="agent", id=qa_agent_id),
                payload={},
            )
        )
        return QaOutcome(
            test_results=results,
            all_passed=True,
            next_state="specialist_review",
            qa_rework_count=qa_rework_count,
        )

    new_rework_count = qa_rework_count + 1
    next_state = "return_to_originating_agent" if new_rework_count < max_attempts else "dead_letter"

    event_ledger.append(
        RunEvent(
            event_id=id_generator.new_id("evt"),
            run_id=run_id,
            attempt_id=attempt_id,
            step_id="qa_validation_against_test_cases",
            aggregate_id=run_id,
            event_type="qa_review_rejected",
            timestamp=clock.now_iso(),
            actor=Actor(type="agent", id=qa_agent_id),
            payload={
                "failing_test_case_ids": failing_ids,
                "target_agent": originating_agent_id,
                "next_state": next_state,
            },
        )
    )

    return QaOutcome(
        test_results=results,
        all_passed=False,
        next_state=next_state,
        qa_rework_count=new_rework_count,
        failing_test_case_ids=failing_ids,
    )
