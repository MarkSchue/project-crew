"""Project Manager query-flow tests (plan milestone M9.3 Definition of
done)."""

from copy import deepcopy

import pytest

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.execution_plane.pm_query_flow import PmQueryFlow

GRAPH = {
    "nodes": [
        {"id": "RISK-001", "type": "risk", "status": "open", "owner": "pm",
         "title": "Delivery risk", "path": "public/risks/RISK-001.md",
         "classification": "internal", "source_refs": [], "cross_references": []},
        {"id": "US-001", "type": "user_story", "status": "ready", "owner": "pm",
         "title": "First user story", "path": "public/user_stories/US-001.md",
         "classification": "internal", "source_refs": [], "cross_references": []},
        {"id": "SECRET-001", "type": "risk", "status": "open", "owner": "pm",
         "title": "confidential thing", "path": "private/x.md",
         "classification": "confidential", "source_refs": [], "cross_references": []},
    ],
    "edges": [],
}


def _flow(graph_index=None, classification="internal"):
    return PmQueryFlow(
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        graph_index=graph_index,
        event_ledger=InMemoryEventLedger(),
        id_generator=SequentialIdGenerator(),
        clock=FixedClock(),
    ), classification


def test_grounded_answer_cites_okf_ids():
    flow, _ = _flow(GRAPH)
    session = flow.create_session(session_id="s1", project_id="PRJ-001", classification="internal")
    answer = flow.ask("s1", "what open risks exist")

    assert answer.grounded is True
    assert "RISK-001" in answer.citations
    assert "RISK-001" in answer.answer  # the id is cited in the answer text


def test_ungrounded_answer_says_so_instead_of_fabricating():
    flow, _ = _flow(GRAPH)
    flow.create_session(session_id="s1", project_id="PRJ-001", classification="internal")
    answer = flow.ask("s1", "zyxwvut qqrrss ttnnmm")

    assert answer.grounded is False
    assert answer.citations == []
    assert "fabricate" in answer.answer


def test_confidential_classification_is_denied():
    flow, _ = _flow(GRAPH)
    flow.create_session(session_id="s1", project_id="PRJ-001", classification="confidential")
    answer = flow.ask("s1", "what open risks exist")

    assert answer.authorized is False
    assert answer.grounded is False
    assert answer.citations == []


def test_confidential_nodes_are_never_cited_from_internal_session():
    flow, _ = _flow(GRAPH)
    flow.create_session(session_id="s1", project_id="PRJ-001", classification="internal")
    answer = flow.ask("s1", "what confidential things exist")

    # SECRET-001 is confidential and must not be cited even though it matches.
    assert "SECRET-001" not in answer.citations
    assert "SECRET-001" not in answer.answer


def test_chat_session_logs_events_and_does_not_mutate_state(tmp_path):
    snapshot = deepcopy(GRAPH)
    flow, _ = _flow(GRAPH)
    flow.project_root = tmp_path
    session = flow.create_session(session_id="s1", project_id="PRJ-001", classification="internal")
    flow.ask("s1", "what open risks exist")

    assert flow.graph_index == snapshot  # graph unchanged
    assert [p for p in tmp_path.rglob("*")] == []  # no files written

    events = flow.event_ledger.events_for_run("s1")
    assert events and all(e.event_type == "chat_message" for e in events)


def test_unknown_session_raises():
    flow, _ = _flow(GRAPH)
    with pytest.raises(KeyError):
        flow.ask("missing", "hello")
