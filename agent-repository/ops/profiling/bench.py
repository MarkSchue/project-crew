#!/usr/bin/env python3
"""Performance/cost profiling benchmark (masterplan section 16.4
economics/operations, plan milestone M8.5).

Measures the platform's deterministic hot paths so the profiling report
is based on real numbers, not estimates:

- registry load (schema + capability + agent + workflow),
- SPOC compilation,
- SQLite save/load round-trips (run state and event append),
- a full vertical-slice flow run.

Output is a JSON summary; commit it alongside the report at
``ops/profiling/result.json``.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.adapters.sqlite import SqliteEventLedger, SqliteRunStateStore
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.control_plane.spoc_compiler import CompileSpocService
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import ProjectRunState, RunManifest, RunStatus
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry

SCHEMA_DIR = REPO_ROOT.parent / "project-template-repository" / "schemas"
REGISTRY_DIR = REPO_ROOT / "tests" / "fixtures" / "registry"


def _timed(name: str, fn, results: dict) -> None:
    started = time.perf_counter()
    fn()
    results[name] = round(time.perf_counter() - started, 6)


def _manifest(run_id: str) -> RunManifest:
    return RunManifest(
        project_id="PRJ-001", spoc_id="SPOC-1", spoc_version="sha256:abc",
        execution_key="ek", run_id=run_id, attempt_id="a1", correlation_id="c1",
        workflow_id="wf", workflow_version="1.0.0", approval_required=True,
    )


def main() -> int:
    results: dict = {}

    # 1. Registry load
    def registry_load() -> None:
        schema = SchemaRegistry(SCHEMA_DIR)
        caps = load_capability_registry(REGISTRY_DIR, schema)
        agents = load_agent_registry(REGISTRY_DIR, schema, caps)
        load_workflow_registry(REGISTRY_DIR, schema)
        assert len(agents) == 3

    _timed("registry_load_seconds", registry_load, results)

    # 2. SPOC compilation
    schema = SchemaRegistry(SCHEMA_DIR)
    caps = load_capability_registry(REGISTRY_DIR, schema)
    agents = load_agent_registry(REGISTRY_DIR, schema, caps)
    workflows = load_workflow_registry(REGISTRY_DIR, schema)
    spoc = load_okf_file(REPO_ROOT / "tests" / "fixtures" / "spoc" / "valid_spoc.md").front_matter
    ids = SequentialIdGenerator()
    compiler = CompileSpocService(
        agent_registry=agents, capability_registry=caps, workflow_registry=workflows,
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=ids),
        clock=FixedClock(), id_generator=ids,
    )

    def compile() -> None:
        compiler.compile(spoc, project_id="PRJ-001")

    _timed("spoc_compile_seconds", compile, results)

    # 3. SQLite round-trips (write amplification probe)
    db_path = Path(tempfile.mkdtemp()) / "bench.db"
    store = SqliteRunStateStore(db_path)
    ledger = SqliteEventLedger(db_path)
    state = ProjectRunState(manifest=_manifest("run-1"), status=RunStatus.CLOSED)

    def sqlite_ops() -> None:
        for _ in range(50):
            store.save("run-1", "a1", state)
            ledger.append(RunEvent(
                event_id=f"e{_}", run_id="run-1", attempt_id="a1", aggregate_id="run-1",
                event_type="probe", timestamp="2026-08-24T09:00:00Z",
                actor=Actor(type="system", id="bench"),
            ))

    _timed("sqlite_50_saves_and_appends_seconds", sqlite_ops, results)

    # 4. Full flow run
    flow = ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=InMemoryEventLedger(),
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        tool_executor=FakeToolExecutor({}),
        clock=FixedClock(), id_generator=SequentialIdGenerator(),
    )

    def flow_run() -> None:
        flow.start(_manifest("run-2"), FlowRunOptions(originating_agent_id="a", qa_agent_id="q", test_cases=[]))

    _timed("full_flow_run_seconds", flow_run, results)

    out = REPO_ROOT / "ops" / "profiling" / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
