"""Runnable ASGI entry for the control plane (dev server).

Wires a full in-memory/local control plane against the workspace's
schemas and registry so ``uvicorn agent_platform.api.main:app`` serves a
working dev instance. Environment overrides:

- ``AGENT_PLATFORM_SCHEMA_DIR`` (default: <workspace>/project-template-repository/schemas)
- ``AGENT_PLATFORM_REGISTRY_DIR`` (default: <workspace>/agent-repository/registry,
  falling back to the test fixture registry so the dev server has data)
- ``AGENT_PLATFORM_ADMIN_TOKEN`` (default: ``dev-token-admin``)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import SequentialIdGenerator, SystemClock
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.api.app import ControlPlaneDeps, create_app
from agent_platform.api.auth import DevAuthProvider, Identity
from agent_platform.control_plane.approval_service import ApprovalService
from agent_platform.control_plane.policy_engine import PolicyEngine
from agent_platform.control_plane.spoc_compiler import CompileSpocService
from agent_platform.execution_plane.pm_query_flow import PmQueryFlow
from agent_platform.execution_plane.project_flow import ProjectExecutionFlow
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.okf_linter import SchemaRegistry

_WORKSPACE = Path(__file__).resolve().parents[4]
_ADMIN_TOKEN = os.environ.get("AGENT_PLATFORM_ADMIN_TOKEN", "dev-token-admin")


def build_app():
    schema_dir = Path(os.environ.get("AGENT_PLATFORM_SCHEMA_DIR", _WORKSPACE / "project-template-repository" / "schemas"))
    registry_dir = Path(os.environ.get("AGENT_PLATFORM_REGISTRY_DIR", _WORKSPACE / "agent-repository" / "registry"))

    schema_registry = SchemaRegistry(schema_dir)

    ids = SequentialIdGenerator()
    clock = SystemClock()

    if not (registry_dir / "capabilities").exists():
        registry_dir = _WORKSPACE / "agent-repository" / "tests" / "fixtures" / "registry"

    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    event_ledger = InMemoryEventLedger()
    policy = PolicyEngine(id_generator=ids, event_ledger=event_ledger)
    approval_gateway = ApprovalService(id_generator=ids, clock=clock)
    approval_gateway_impl = InMemoryApprovalGateway(auto_approve=False)

    compile_service = CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=policy,
        clock=clock,
        id_generator=ids,
        approval_gateway=approval_gateway_impl,
    )

    flow = ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=event_ledger,
        approval_gateway=approval_gateway_impl,
        policy=policy,
        tool_executor=None,  # real tool executor is a follow-up (ADR-020)
        clock=clock,
        id_generator=ids,
    )

    auth = DevAuthProvider(
        {_ADMIN_TOKEN: Identity(actor_type="human", actor_id="admin", project_id=None, roles=frozenset({"admin"}))}
    )

    graph_index = None
    project_dir = Path(os.environ.get("AGENT_PLATFORM_PROJECT_DIR", _WORKSPACE / "active-project-repo"))
    graph_path = project_dir / "public" / "knowledge" / "graph_index.json"
    if graph_path.exists():
        graph_index = json.loads(graph_path.read_text(encoding="utf-8"))

    pm_query_flow = PmQueryFlow(
        policy=policy,
        graph_index=graph_index,
        project_root=project_dir,
        event_ledger=event_ledger,
        id_generator=ids,
        clock=clock,
    )

    deps = ControlPlaneDeps(
        compile_service=compile_service,
        run_state_store=flow.run_state_store,
        event_ledger=event_ledger,
        approval_gateway=approval_gateway_impl,
        flow=flow,
        auth_provider=auth,
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        schema_registry=schema_registry,
        graph_index=graph_index,
        pm_query_flow=pm_query_flow,
    )
    return create_app(deps)


app = build_app()
