"""Graph and chat REST endpoint tests (plan milestone M9.2 Definition of
done)."""

import pytest
from fastapi.testclient import TestClient

from agent_platform.adapters.clock_and_ids import SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.api.app import ControlPlaneDeps, create_app
from agent_platform.api.auth import DevAuthProvider, Identity
from agent_platform.execution_plane.pm_query_flow import PmQueryFlow

TOKEN = "dev-token-admin"

GRAPH = {
    "nodes": [
        {"id": "RISK-001", "type": "risk", "status": "open", "owner": "pm",
         "title": "Delivery risk", "path": "public/risks/RISK-001.md",
         "classification": "internal", "source_refs": [], "cross_references": []},
        {"id": "US-001", "type": "user_story", "status": "ready", "owner": "pm",
         "title": "First user story", "path": "public/user_stories/US-001.md",
         "classification": "internal", "source_refs": [], "cross_references": []},
    ],
    "edges": [{"type": "tested_by", "source": "US-001", "target": "RISK-001"}],
}


@pytest.fixture
def client():
    ids = SequentialIdGenerator()
    policy = LocalDevPolicyDecisionPoint(decision_id_generator=ids)
    event_ledger = InMemoryEventLedger()
    pm_query_flow = PmQueryFlow(
        policy=policy,
        graph_index=GRAPH,
        event_ledger=event_ledger,
        id_generator=ids,
    )
    auth = DevAuthProvider(
        {TOKEN: Identity(actor_type="human", actor_id="admin", project_id=None, roles=frozenset({"admin"}))}
    )
    deps = ControlPlaneDeps(
        auth_provider=auth,
        graph_index=GRAPH,
        pm_query_flow=pm_query_flow,
    )
    return TestClient(create_app(deps))


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_graph_served_directly(client):
    response = client.get("/api/v1/graph", headers=_auth())
    assert response.status_code == 200
    assert response.json() == GRAPH


def test_graph_node_and_404(client):
    node = client.get("/api/v1/graph/nodes/RISK-001", headers=_auth())
    assert node.status_code == 200
    assert node.json()["id"] == "RISK-001"

    missing = client.get("/api/v1/graph/nodes/NOPE", headers=_auth())
    assert missing.status_code == 404


def test_graph_neighbors(client):
    response = client.get("/api/v1/graph/nodes/US-001/neighbors", headers=_auth())
    assert response.status_code == 200
    assert [n["id"] for n in response.json()["neighbors"]] == ["RISK-001"]


def test_chat_session_and_message_round_trip(client):
    session = client.post(
        "/api/v1/chat/sessions",
        json={"project_id": "PRJ-001", "classification": "internal"},
        headers=_auth(),
    )
    assert session.status_code == 201
    session_id = session.json()["session_id"]

    message = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "what open risks exist"},
        headers=_auth(),
    )
    assert message.status_code == 200
    body = message.json()
    assert body["grounded"] is True
    assert "RISK-001" in body["citations"]


def test_chat_stream(client):
    session_id = client.post(
        "/api/v1/chat/sessions", json={"project_id": "PRJ-001"}, headers=_auth()
    ).json()["session_id"]
    client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "what open risks exist"},
        headers=_auth(),
    )
    stream = client.get(f"/api/v1/chat/sessions/{session_id}/stream", headers=_auth())
    assert stream.status_code == 200
    assert "event: chat_message" in stream.text
    assert "event: done" in stream.text


def test_graph_requires_auth(client):
    assert client.get("/api/v1/graph").status_code == 401
