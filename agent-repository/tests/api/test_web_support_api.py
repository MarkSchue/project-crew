"""Web-support API tests: schemas, artifacts, approvals list, graph style,
and static UI serving (plan milestone M9.4/M9.5 Definition of done)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.api.app import ControlPlaneDeps, create_app
from agent_platform.api.auth import DevAuthProvider, Identity
from agent_platform.domain.run import ApprovalRequest

TOKEN = "dev-token-admin"
SCHEMA_DIR = Path(__file__).resolve().parents[3] / "project-template-repository" / "schemas"
WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(tmp_path):
    artifact = tmp_path / "public" / "risks" / "RISK-001.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "---\nschema_version: okf/1.1\nid: RISK-001\ntype: risk\ntitle: R\nstatus: open\n"
        "classification: internal\nowner: pm\ncreated_at: 2026-08-24T09:00:00Z\n"
        "updated_at: 2026-08-24T09:00:00Z\ntags: []\nsource_refs: []\nrelations: []\n"
        "provenance: {created_by_type: system, created_by_id: t}\n---\n# R\n",
        encoding="utf-8",
    )

    graph_index = {
        "nodes": [
            {"id": "RISK-001", "type": "risk", "status": "open", "owner": "pm",
             "title": "R", "path": "public/risks/RISK-001.md",
             "classification": "internal", "source_refs": [], "cross_references": []},
        ],
        "edges": [],
    }

    approvals = InMemoryApprovalGateway()
    approvals.request_approval(ApprovalRequest(approval_id="a1", scope="production_change", subject="SPOC-1"))

    auth = DevAuthProvider(
        {TOKEN: Identity(actor_type="human", actor_id="admin", project_id=None, roles=frozenset({"admin"}))}
    )
    deps = ControlPlaneDeps(
        auth_provider=auth,
        graph_index=graph_index,
        schema_dir=SCHEMA_DIR,
        project_root=tmp_path,
        web_dir=WEB_DIR,
        graph_style={"risk": {"color": "#dc2626", "icon": "warning"}},
        approval_gateway=approvals,
    )
    return TestClient(create_app(deps))


def test_serves_spoc_schema(client):
    response = client.get("/api/v1/schemas/spoc.schema.json", headers=_auth())
    assert response.status_code == 200
    assert "required" in response.json()
    assert "id" in response.json()["required"]


def test_schema_path_traversal_rejected(client):
    response = client.get("/api/v1/schemas/../../etc/passwd", headers=_auth())
    assert response.status_code in (404, 403)


def test_artifact_served_by_id(client):
    response = client.get("/api/v1/artifacts/RISK-001", headers=_auth())
    assert response.status_code == 200
    assert response.json()["id"] == "RISK-001"
    assert response.json()["front_matter"]["type"] == "risk"
    assert "# R" in response.json()["body"]


def test_artifact_unknown_id_404(client):
    assert client.get("/api/v1/artifacts/NOPE", headers=_auth()).status_code == 404


def test_approvals_listed(client):
    response = client.get("/api/v1/approvals", headers=_auth())
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(i["approval_id"] == "a1" for i in items)


def test_graph_style_served(client):
    response = client.get("/api/v1/graph/style", headers=_auth())
    assert response.status_code == 200
    assert response.json()["types"]["risk"]["color"] == "#dc2626"


def test_root_redirects_to_ui(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (307, 302)


def test_ui_serves_index_html(client):
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "Project Crew" in response.text
