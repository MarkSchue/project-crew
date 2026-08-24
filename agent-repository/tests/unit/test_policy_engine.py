"""Policy engine tests (plan milestone M5.1 Definition of done)."""

from agent_platform.adapters.clock_and_ids import SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger
from agent_platform.control_plane.approval_matrix import MANDATORY_APPROVAL_ACTIONS
from agent_platform.control_plane.policy_engine import PolicyEngine


def _engine(*, with_ledger=False):
    ids = SequentialIdGenerator()
    ledger = InMemoryEventLedger() if with_ledger else None
    return PolicyEngine(id_generator=ids, event_ledger=ledger), ids, ledger


def test_hard_deny_action_is_denied():
    engine, _, _ = _engine()
    decision = engine.evaluate(action="write_to_production", context={})
    assert decision.allowed is False
    assert decision.reason.startswith("hard_deny")


def test_classification_denied_when_not_in_allowlist():
    engine, _, _ = _engine()
    decision = engine.evaluate(
        action="repository.read",
        context={"classification": "confidential", "allowed_classifications": ["internal"]},
    )
    assert decision.allowed is False
    assert "classification_denied" in decision.reason


def test_mandatory_approval_action_denied_without_approval():
    engine, _, _ = _engine()
    decision = engine.evaluate(action="production_change", context={})
    assert decision.allowed is False
    assert decision.reason == "requires_human_approval"


def test_mandatory_approval_action_allowed_with_approval():
    engine, _, _ = _engine()
    decision = engine.evaluate(action="production_change", context={"approved": True})
    assert decision.allowed is True


def test_default_allow_for_ordinary_action():
    engine, _, _ = _engine()
    decision = engine.evaluate(action="repository.read", context={})
    assert decision.allowed is True


def test_every_mandatory_action_is_covered_by_matrix():
    engine, _, _ = _engine()
    for action in MANDATORY_APPROVAL_ACTIONS:
        assert engine.evaluate(action=action, context={}).allowed is False


def test_decision_is_logged_and_emitted():
    engine, ids, ledger = _engine(with_ledger=True)
    decision = engine.evaluate(action="production_change", context={"run_id": "run_1", "approved": True})
    assert decision in engine.decisions
    events = ledger.events_for_run("run_1")
    assert any(e.event_type == "policy_decision" for e in events)
    policy_event = next(e for e in events if e.event_type == "policy_decision")
    assert policy_event.policy_decision_id == decision.policy_decision_id


def test_fail_closed_on_internal_error():
    # Force an internal error: a list is unhashable, so the membership
    # checks raise TypeError inside _decide.
    engine, _, _ = _engine()
    decision = engine.evaluate(action=["unhashable"], context={})
    assert decision.allowed is False
    assert decision.reason.startswith("policy_engine_error")
