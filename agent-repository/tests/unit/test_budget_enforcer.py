"""Budget enforcer tests (plan milestone M5.4 Definition of done)."""

import pytest

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger
from agent_platform.control_plane.budget_enforcer import BudgetEnforcer, BudgetLimitExceededError
from agent_platform.domain.run import CostState


def _enforcer(*, with_ledger=False):
    ledger = InMemoryEventLedger() if with_ledger else None
    return BudgetEnforcer(
        event_ledger=ledger,
        clock=FixedClock() if with_ledger else None,
        id_generator=SequentialIdGenerator() if with_ledger else None,
    ), ledger


def test_cost_limit_exceeded():
    enforcer, _ = _enforcer()
    cost_state = CostState(spent_usd=7.0, max_total_cost_usd=10.0)
    with pytest.raises(BudgetLimitExceededError) as exc_info:
        enforcer.enforce(
            run_id="run_1", attempt_id="attempt_1",
            cost_state=cost_state, additional_cost_usd=4.0, max_total_cost_usd=10.0,
        )
    assert exc_info.value.limit_name == "max_total_cost_usd"


def test_runtime_limit_exceeded():
    enforcer, _ = _enforcer()
    with pytest.raises(BudgetLimitExceededError) as exc_info:
        enforcer.enforce(
            run_id="run_1", attempt_id="attempt_1",
            elapsed_seconds=1801, max_runtime_seconds=1800,
        )
    assert exc_info.value.limit_name == "max_runtime_seconds"


def test_delegation_depth_limit_exceeded():
    enforcer, _ = _enforcer()
    with pytest.raises(BudgetLimitExceededError) as exc_info:
        enforcer.enforce(
            run_id="run_1", attempt_id="attempt_1",
            delegation_depth=2, max_delegation_depth=1,
        )
    assert exc_info.value.limit_name == "max_delegation_depth"


def test_child_calls_limit_exceeded():
    enforcer, _ = _enforcer()
    with pytest.raises(BudgetLimitExceededError) as exc_info:
        enforcer.enforce(
            run_id="run_1", attempt_id="attempt_1",
            child_agent_calls=4, max_child_agent_calls=3,
        )
    assert exc_info.value.limit_name == "max_child_agent_calls"


def test_within_limits_passes_and_no_event_emitted():
    enforcer, ledger = _enforcer(with_ledger=True)
    enforcer.enforce(
        run_id="run_1", attempt_id="attempt_1",
        cost_state=CostState(spent_usd=1.0, max_total_cost_usd=10.0),
        additional_cost_usd=1.0,
        elapsed_seconds=100, max_runtime_seconds=1800,
        delegation_depth=1, max_delegation_depth=1,
        child_agent_calls=3, max_child_agent_calls=3,
        max_total_cost_usd=10.0,
    )
    assert ledger.events_for_run("run_1") == []


def test_exceeding_limit_emits_budget_event():
    enforcer, ledger = _enforcer(with_ledger=True)
    with pytest.raises(BudgetLimitExceededError):
        enforcer.enforce(
            run_id="run_1", attempt_id="attempt_1",
            elapsed_seconds=9999, max_runtime_seconds=100,
        )
    events = ledger.events_for_run("run_1")
    assert any(e.event_type == "budget_threshold_reached" for e in events)
    event = next(e for e in events if e.event_type == "budget_threshold_reached")
    assert event.payload["limit_name"] == "max_runtime_seconds"
