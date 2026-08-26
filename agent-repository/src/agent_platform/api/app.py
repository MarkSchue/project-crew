"""FastAPI control-plane service (masterplan section 17.2, plan milestone
M6.1) and SSE/RBAC (M6.5).

``create_app(deps)`` builds the REST surface:

- ``POST /api/v1/spocs/validate`` / ``POST /api/v1/spocs/compile``
- ``POST /api/v1/runs``, ``GET /api/v1/runs`` (paginated)
- ``GET /api/v1/runs/{run_id}`` (with optimistic-concurrency ETag)
- ``POST /api/v1/runs/{run_id}/cancel`` / ``/resume`` (If-Match required)
- ``GET /api/v1/runs/{run_id}/events`` (Server-Sent Events, RBAC-scoped)
- ``GET/POST /api/v1/approvals/{approval_id}`` / ``.../resolve``
- ``GET /api/v1/registry/agents`` / ``.../capabilities`` (paginated)

Cross-cutting (M6.1 DoD): dev bearer-token auth (``DevAuthProvider``),
project-scoped RBAC, idempotency keys on mutating endpoints, optimistic
concurrency on state-changing calls, pagination on list endpoints, and
``X-Correlation-ID`` echoed end-to-end.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent_platform.api.auth import DevAuthProvider, Identity
from agent_platform.application.ports.approval_gateway import ApprovalGateway
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.application.ports.run_state_store import RunStateStore
from agent_platform.control_plane.spoc_compiler import CompileSpocService
from agent_platform.domain.run import ProjectRunState, RunManifest, RunStatus
from agent_platform.execution_plane.pm_query_flow import PmQueryFlow
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow
from agent_platform.registries.agent_registry import AgentRegistry
from agent_platform.registries.capability_registry import CapabilityRegistry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry


class IdempotencyStore:
    def __init__(self) -> None:
        self._results: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        return self._results.get(key)

    def put(self, key: str, result: dict) -> None:
        self._results[key] = result


@dataclass
class ControlPlaneDeps:
    compile_service: CompileSpocService | None = None
    run_state_store: RunStateStore | None = None
    event_ledger: EventLedger | None = None
    approval_gateway: ApprovalGateway | None = None
    flow: ProjectExecutionFlow | None = None
    auth_provider: DevAuthProvider = field(default_factory=DevAuthProvider)
    agent_registry: AgentRegistry | None = None
    capability_registry: CapabilityRegistry | None = None
    schema_registry: SchemaRegistry | None = None
    idempotency_store: IdempotencyStore = field(default_factory=IdempotencyStore)
    graph_index: dict | None = None
    pm_query_flow: PmQueryFlow | None = None
    schema_dir: Path | None = None
    project_root: Path | None = None
    web_dir: Path | None = None
    graph_style: dict | None = None


class SpocValidateRequest(BaseModel):
    spoc: dict


class SpocCompileRequest(BaseModel):
    project_id: str
    spoc: dict


class StartRunRequest(BaseModel):
    manifest: dict
    originating_agent_id: str
    qa_agent_id: str
    test_cases: list[dict] = Field(default_factory=list)
    human_plan_approved: bool = True
    human_acceptance_approved: bool = True
    max_qa_attempts: int = 2


class ResumeRunRequest(BaseModel):
    originating_agent_id: str
    qa_agent_id: str
    test_cases: list[dict] = Field(default_factory=list)
    human_plan_approved: bool = True
    human_acceptance_approved: bool = True
    max_qa_attempts: int = 2


class ResolveApprovalRequest(BaseModel):
    approved: bool
    reason: str | None = None


class ChatSessionCreateRequest(BaseModel):
    project_id: str
    classification: str = "internal"


class ChatMessageRequest(BaseModel):
    content: str


def _etag(state: ProjectRunState) -> str:
    return hashlib.sha256(state.model_dump_json().encode("utf-8")).hexdigest()


def _paginate(items: list[dict], offset: int, limit: int) -> dict:
    return {"items": items[offset : offset + limit], "total": len(items), "offset": offset, "limit": limit}


def create_app(deps: ControlPlaneDeps) -> FastAPI:
    app = FastAPI(title="Agent Platform Control Plane", version="0.1.0")
    app.state.deps = deps

    def _identity(request: Request) -> Identity:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        identity = deps.auth_provider.authenticate(auth[7:])
        if identity is None:
            raise HTTPException(status_code=403, detail="invalid bearer token")
        return identity

    def _authorize_project(identity: Identity, project_id: str) -> None:
        if not identity.can_access_project(project_id):
            raise HTTPException(status_code=403, detail="insufficient project scope")

    def _load_latest(run_id: str) -> ProjectRunState:
        attempt_id = deps.run_state_store.latest_attempt_id(run_id)
        if attempt_id is None:
            raise HTTPException(status_code=404, detail=f"unknown run '{run_id}'")
        state = deps.run_state_store.load(run_id, attempt_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"unknown run '{run_id}'")
        return state

    def _options(body: StartRunRequest | ResumeRunRequest) -> FlowRunOptions:
        return FlowRunOptions(
            originating_agent_id=body.originating_agent_id,
            qa_agent_id=body.qa_agent_id,
            test_cases=body.test_cases,
            human_plan_approved=body.human_plan_approved,
            human_acceptance_approved=body.human_acceptance_approved,
            max_qa_attempts=body.max_qa_attempts,
        )

    @app.middleware("http")
    async def _correlation_id_middleware(request: Request, call_next):
        cid = request.headers.get("x-correlation-id", "")
        response = await call_next(request)
        if cid:
            response.headers["x-correlation-id"] = cid
        return response

    @app.get("/api/v1/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/v1/spocs/validate")
    def validate_spoc(body: SpocValidateRequest, request: Request) -> dict:
        _identity(request)
        validator = deps.schema_registry.validator_for_filename("spoc.schema.json")
        issues = [
            f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(body.spoc), key=lambda e: list(e.path))
        ]
        return {"valid": not issues, "issues": issues}

    @app.post("/api/v1/spocs/compile")
    def compile_spoc(body: SpocCompileRequest, request: Request) -> dict:
        identity = _identity(request)
        _authorize_project(identity, body.project_id)
        manifest = deps.compile_service.compile(body.spoc, project_id=body.project_id)
        return {"manifest": manifest.model_dump()}

    @app.post("/api/v1/runs", status_code=201)
    def start_run(body: StartRunRequest, request: Request) -> dict:
        identity = _identity(request)
        manifest = RunManifest.model_validate(body.manifest)
        _authorize_project(identity, manifest.project_id)

        idempotency_key = request.headers.get("idempotency-key")
        if idempotency_key:
            cached = deps.idempotency_store.get(idempotency_key)
            if cached is not None:
                return cached

        state = deps.flow.start(manifest, _options(body))
        result = {"run_id": manifest.run_id, "status": state.status.value}
        if idempotency_key:
            deps.idempotency_store.put(idempotency_key, result)
        return result

    @app.get("/api/v1/runs")
    def list_runs(request: Request, offset: int = 0, limit: int = 20) -> dict:
        identity = _identity(request)
        items = []
        for run_id in deps.run_state_store.list_run_ids():
            attempt_id = deps.run_state_store.latest_attempt_id(run_id)
            if attempt_id is None:
                continue
            state = deps.run_state_store.load(run_id, attempt_id)
            if not identity.can_access_project(state.manifest.project_id):
                continue
            items.append(
                {
                    "run_id": run_id,
                    "project_id": state.manifest.project_id,
                    "status": state.status.value,
                }
            )
        return _paginate(items, offset, limit)

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str, request: Request):
        identity = _identity(request)
        state = _load_latest(run_id)
        _authorize_project(identity, state.manifest.project_id)
        return JSONResponseWithEtag(state)

    @app.post("/api/v1/runs/{run_id}/cancel")
    def cancel_run(run_id: str, request: Request) -> dict:
        identity = _identity(request)
        state = _load_latest(run_id)
        _authorize_project(identity, state.manifest.project_id)
        _require_if_match(request, state)
        state.status = RunStatus.CANCELLED
        deps.run_state_store.save(run_id, state.manifest.attempt_id, state)
        return {"run_id": run_id, "status": state.status.value}

    @app.post("/api/v1/runs/{run_id}/resume")
    def resume_run(run_id: str, body: ResumeRunRequest, request: Request) -> dict:
        identity = _identity(request)
        state = _load_latest(run_id)
        _authorize_project(identity, state.manifest.project_id)
        _require_if_match(request, state)
        resumed = deps.flow.resume(run_id, state.manifest.attempt_id, _options(body))
        return {"run_id": run_id, "status": resumed.status.value}

    @app.get("/api/v1/runs/{run_id}/events")
    def run_events(run_id: str, request: Request) -> StreamingResponse:
        identity = _identity(request)
        state = _load_latest(run_id)
        _authorize_project(identity, state.manifest.project_id)

        events = deps.event_ledger.events_for_run(run_id)

        def gen():
            for event in events:
                yield f"event: run_event\ndata: {event.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/v1/approvals")
    def list_approvals(request: Request, offset: int = 0, limit: int = 50) -> dict:
        _identity(request)
        items = [
            {
                "approval_id": a.approval_id,
                "scope": a.scope,
                "subject": a.subject,
                "status": a.status,
                "requested_at": a.requested_at,
            }
            for a in deps.approval_gateway.list_approvals()
        ]
        return _paginate(items, offset, limit)

    @app.get("/api/v1/approvals/{approval_id}")
    def get_approval(approval_id: str, request: Request) -> dict:
        _identity(request)
        return {"approval_id": approval_id, "status": deps.approval_gateway.get_status(approval_id)}

    @app.post("/api/v1/approvals/{approval_id}/resolve")
    def resolve_approval(approval_id: str, body: ResolveApprovalRequest, request: Request) -> dict:
        _identity(request)
        deps.approval_gateway.resolve(approval_id, approved=body.approved, reason=body.reason)
        return {"approval_id": approval_id, "status": deps.approval_gateway.get_status(approval_id)}

    @app.get("/api/v1/registry/agents")
    def list_agents(request: Request, offset: int = 0, limit: int = 20) -> dict:
        _identity(request)
        items = [
            {
                "agent_id": agent.agent_id,
                "version": agent.version,
                "status": agent.status,
                "capabilities": [c.id for c in agent.capabilities],
            }
            for agent in (deps.agent_registry or [])
        ]
        return _paginate(items, offset, limit)

    @app.get("/api/v1/registry/capabilities")
    def list_capabilities(request: Request, offset: int = 0, limit: int = 20) -> dict:
        _identity(request)
        items = [
            {"id": cid, "version": entry.version, "risk_level": entry.risk_level}
            for cid, entry in sorted((deps.capability_registry.entries or {}).items())
        ]
        return _paginate(items, offset, limit)

    # -- knowledge graph (M9.2) ------------------------------------------------

    def _require_graph() -> dict:
        if deps.graph_index is None:
            raise HTTPException(status_code=404, detail="graph index not available")
        return deps.graph_index

    @app.get("/api/v1/graph")
    def get_graph(request: Request) -> dict:
        """Serve the graph directly from the pre-loaded graph_index.json
        (no per-request OKF re-parsing)."""
        _identity(request)
        return _require_graph()

    @app.get("/api/v1/graph/style")
    def get_graph_style(request: Request) -> dict:
        """Serve the type -> color/icon style table for the graph view and
        its legend."""
        _identity(request)
        if deps.graph_style is None:
            raise HTTPException(status_code=404, detail="graph style not available")
        return {"types": deps.graph_style}

    @app.get("/api/v1/graph/nodes/{node_id}")
    def get_graph_node(node_id: str, request: Request) -> dict:
        _identity(request)
        graph = _require_graph()
        for node in graph.get("nodes", []):
            if node.get("id") == node_id:
                return node
        raise HTTPException(status_code=404, detail=f"unknown node '{node_id}'")

    @app.get("/api/v1/graph/nodes/{node_id}/neighbors")
    def get_graph_neighbors(node_id: str, request: Request) -> dict:
        _identity(request)
        graph = _require_graph()
        nodes_by_id = {n.get("id"): n for n in graph.get("nodes", [])}
        if node_id not in nodes_by_id:
            raise HTTPException(status_code=404, detail=f"unknown node '{node_id}'")

        neighbors: dict[str, dict] = {}
        for edge in graph.get("edges", []):
            if edge.get("source") == node_id:
                neighbors[edge["target"]] = nodes_by_id.get(edge["target"], {})
            elif edge.get("target") == node_id:
                neighbors[edge["source"]] = nodes_by_id.get(edge["source"], {})
        return {"node_id": node_id, "neighbors": list(neighbors.values())}

    @app.get("/api/v1/schemas/{filename}")
    def get_schema(filename: str, request: Request) -> dict:
        """Serve a JSON Schema file (single source of truth for the SPOC
        editor's client-side validation)."""
        _identity(request)
        if deps.schema_dir is None:
            raise HTTPException(status_code=503, detail="schemas not configured")
        if Path(filename).name != filename or not filename.endswith(".schema.json"):
            raise HTTPException(status_code=404, detail="unknown schema")
        schema_path = deps.schema_dir / filename
        if not schema_path.exists():
            raise HTTPException(status_code=404, detail="unknown schema")
        return json.loads(schema_path.read_text(encoding="utf-8"))

    @app.get("/api/v1/artifacts/{node_id}")
    def get_artifact(node_id: str, request: Request) -> dict:
        """Serve an OKF artifact (front matter + body) by stable node id for
        the document viewer."""
        _identity(request)
        graph = _require_graph()
        node = next((n for n in graph.get("nodes", []) if n.get("id") == node_id), None)
        if node is None:
            raise HTTPException(status_code=404, detail=f"unknown node '{node_id}'")
        if deps.project_root is None or not node.get("path"):
            raise HTTPException(status_code=503, detail="artifact store not configured")

        root = deps.project_root.resolve()
        target = (root / node["path"]).resolve()
        if root not in target.parents:
            raise HTTPException(status_code=403, detail="artifact path escapes project root")
        if not target.exists():
            raise HTTPException(status_code=404, detail="artifact file missing")

        document = load_okf_file(target)
        return {
            "id": node_id,
            "path": node["path"],
            "front_matter": document.front_matter,
            "body": document.body,
        }

    # -- Project Manager chat (M9.2 surface, M9.3 flow) -------------------------

    @app.post("/api/v1/chat/sessions", status_code=201)
    def create_chat_session(body: ChatSessionCreateRequest, request: Request) -> dict:
        identity = _identity(request)
        _authorize_project(identity, body.project_id)
        if deps.pm_query_flow is None:
            raise HTTPException(status_code=503, detail="chat flow not configured")
        import uuid

        session_id = f"chat-{uuid.uuid4().hex[:12]}"
        session = deps.pm_query_flow.create_session(
            session_id=session_id, project_id=body.project_id, classification=body.classification
        )
        return {"session_id": session.session_id, "classification": session.classification}

    @app.post("/api/v1/chat/sessions/{session_id}/messages")
    def post_chat_message(session_id: str, body: ChatMessageRequest, request: Request) -> dict:
        _identity(request)
        if deps.pm_query_flow is None:
            raise HTTPException(status_code=503, detail="chat flow not configured")
        try:
            answer = deps.pm_query_flow.ask(session_id, body.content)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "session_id": answer.session_id,
            "answer": answer.answer,
            "citations": answer.citations,
            "grounded": answer.grounded,
            "authorized": answer.authorized,
        }

    @app.get("/api/v1/chat/sessions/{session_id}/stream")
    def stream_chat_session(session_id: str, request: Request) -> StreamingResponse:
        _identity(request)
        if deps.pm_query_flow is None:
            raise HTTPException(status_code=503, detail="chat flow not configured")
        try:
            session = deps.pm_query_flow.get_session(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        def gen():
            for message in session.messages:
                payload = json.dumps(
                    {"role": message.role, "content": message.content, "citations": message.citations}
                )
                yield f"event: chat_message\ndata: {payload}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    def _require_if_match(request: Request, state: ProjectRunState) -> None:
        if request.headers.get("if-match") != _etag(state):
            raise HTTPException(status_code=409, detail="version conflict (If-Match mismatch)")

    if deps.web_dir is not None:
        from fastapi.staticfiles import StaticFiles

        app.mount("/ui", StaticFiles(directory=str(deps.web_dir), html=True), name="ui")

        @app.get("/", include_in_schema=False)
        def index() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

    return app


def JSONResponseWithEtag(state: ProjectRunState):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={"run_id": state.manifest.run_id, "status": state.status.value, "completed_steps": state.completed_steps},
        headers={"ETag": _etag(state)},
    )
