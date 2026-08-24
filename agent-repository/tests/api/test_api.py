"""FastAPI control-plane integration tests (plan milestones M6.1 and
M6.5 Definition of done)."""

import pytest
from fastapi.testclient import TestClient

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.api.app import ControlPlaneDeps, create_app
from agent_platform.api.auth import DevAuthProvider, Identity
from agent_platform.control_plane.policy_engine import PolicyEngine
from agent_platform.control_plane.spoc_compiler import CompileSpocService
from agent_platform.execution_plane.project_flow import ProjectExecutionFlow
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry

PROJECT_A = "PRJ-001"
PROJECT_B = "PRJ-002"
TOKEN_A = "dev-token-PRJ-001"
TOKEN_B = "dev-token-PRJ-002"
ADMIN = "dev-token-admin"


@pytest.fixture
def client(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    ids = SequentialIdGenerator()
    event_ledger = InMemoryEventLedger()
    approval_gateway = InMemoryApprovalGateway()
    policy = PolicyEngine(id_generator=ids, event_ledger=event_ledger)
    compile_service = CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=policy,
        clock=FixedClock(),
        id_generator=ids,
        approval_gateway=approval_gateway,
    )
    flow = ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=event_ledger,
        approval_gateway=approval_gateway,
        policy=policy,
        tool_executor=FakeToolExecutor({}),
        clock=FixedClock(),
        id_generator=ids,
    )

    auth = DevAuthProvider(
        {
            TOKEN_A: Identity(actor_type="human", actor_id="user-a", project_id=PROJECT_A, roles=frozenset()),
            TOKEN_B: Identity(actor_type="human", actor_id="user-b", project_id=PROJECT_B, roles=frozenset()),
            ADMIN: Identity(actor_type="human", actor_id="admin", project_id=None, roles=frozenset({"admin"})),
        }
    )

    deps = ControlPlaneDeps(
        compile_service=compile_service,
        run_state_store=flow.run_state_store,
        event_ledger=event_ledger,
        approval_gateway=approval_gateway,
        flow=flow,
        auth_provider=auth,
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        schema_registry=schema_registry,
    )
    return TestClient(create_app(deps))


def _spoc(fixtures_dir):
    return load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_and_401_without_token(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/runs").status_code == 401
    assert client.get("/api/v1/registry/agents").status_code == 401


def test_invalid_token_403(client):
    response = client.get("/api/v1/runs", headers=_auth("not-a-token"))
    assert response.status_code == 403


def test_spoc_validate_and_compile(client, fixtures_dir):
    spoc = _spoc(fixtures_dir)
    validate = client.post("/api/v1/spocs/validate", json={"spoc": spoc}, headers=_auth(TOKEN_A))
    assert validate.status_code == 200
    assert validate.json()["valid"] is True

    compile_response = client.post(
        "/api/v1/spocs/compile", json={"project_id": PROJECT_A, "spoc": spoc}, headers=_auth(TOKEN_A)
    )
    assert compile_response.status_code == 200
    assert compile_response.json()["manifest"]["project_id"] == PROJECT_A


def test_compile_enforced_project_scope(client, fixtures_dir):
    spoc = _spoc(fixtures_dir)
    # User B (project B) cannot compile a SPOC for project A.
    response = client.post(
        "/api/v1/spocs/compile", json={"project_id": PROJECT_A, "spoc": spoc}, headers=_auth(TOKEN_B)
    )
    assert response.status_code == 403


def test_run_lifecycle_with_idempotency_and_optimistic_concurrency(client, fixtures_dir):
    spoc = _spoc(fixtures_dir)
    manifest = client.post(
        "/api/v1/spocs/compile", json={"project_id": PROJECT_A, "spoc": spoc}, headers=_auth(TOKEN_A)
    ).json()["manifest"]

    payload = {
        "manifest": manifest,
        "originating_agent_id": "architecture_writer",
        "qa_agent_id": "qa_evaluator",
        "test_cases": [],
    }
    headers = dict(_auth(TOKEN_A), **{"Idempotency-Key": "idem-1"})
    first = client.post("/api/v1/runs", json=payload, headers=headers)
    second = client.post("/api/v1/runs", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.json()["run_id"] == first.json()["run_id"]  # idempotent

    run_id = first.json()["run_id"]
    got = client.get(f"/api/v1/runs/{run_id}", headers=_auth(TOKEN_A))
    assert got.status_code == 200
    etag = got.headers["etag"]

    # Optimistic concurrency: a stale If-Match is rejected with 409.
    conflict = client.post(f"/api/v1/runs/{run_id}/cancel", headers=dict(_auth(TOKEN_A), **{"If-Match": "stale"}))
    assert conflict.status_code == 409

    cancelled = client.post(f"/api/v1/runs/{run_id}/cancel", headers=dict(_auth(TOKEN_A), **{"If-Match": etag}))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_pagination_on_list_endpoints(client, fixtures_dir):
    # Registry list endpoints are paginated.
    agents = client.get("/api/v1/registry/agents", params={"offset": 0, "limit": 2}, headers=_auth(TOKEN_A))
    assert agents.status_code == 200
    assert "total" in agents.json()
    assert len(agents.json()["items"]) <= 2

    capabilities = client.get(
        "/api/v1/registry/capabilities", params={"offset": 0, "limit": 2}, headers=_auth(TOKEN_A)
    )
    assert capabilities.status_code == 200
    assert "total" in capabilities.json()


def test_correlation_id_echoed(client, fixtures_dir):
    spoc = _spoc(fixtures_dir)
    response = client.post(
        "/api/v1/spocs/validate",
        json={"spoc": spoc},
        headers=dict(_auth(TOKEN_A), **{"X-Correlation-ID": "corr-123"}),
    )
    assert response.headers.get("x-correlation-id") == "corr-123"


def test_sse_events_rbac_blocks_cross_project(client, fixtures_dir):
    spoc = _spoc(fixtures_dir)
    manifest = client.post(
        "/api/v1/spocs/compile", json={"project_id": PROJECT_A, "spoc": spoc}, headers=_auth(TOKEN_A)
    ).json()["manifest"]
    run_id = client.post(
        "/api/v1/runs",
        json={"manifest": manifest, "originating_agent_id": "architecture_writer", "qa_agent_id": "qa_evaluator", "test_cases": []},
        headers=_auth(TOKEN_A),
    ).json()["run_id"]

    # Project A user can stream events.
    events = client.get(f"/api/v1/runs/{run_id}/events", headers=_auth(TOKEN_A))
    assert events.status_code == 200
    assert "text/event-stream" in events.headers["content-type"]
    body = events.text
    assert "run_event" in body

    # Project B user cannot read project A's run events (M6.5 DoD).
    blocked = client.get(f"/api/v1/runs/{run_id}/events", headers=_auth(TOKEN_B))
    assert blocked.status_code == 403
