"""Phase 7 project-management workflow tests (plan section 12 milestones
M7.1-M7.6 Definition of done)."""

import pytest

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger, InMemoryRunStateStore
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.adapters.tool_executor import FakeToolExecutor
from agent_platform.control_plane.approval_service import ApprovalService
from agent_platform.control_plane.spoc_compiler import CompileSpocService, SpocCompilationError
from agent_platform.execution_plane.flows.change_request import evaluate_change_request
from agent_platform.execution_plane.flows.okf_render import okf_front_matter, render_okf
from agent_platform.execution_plane.flows.planning_baseline import run_planning_baseline
from agent_platform.execution_plane.flows.project_closure import ClosureResult, render_closure_artifact, run_project_closure
from agent_platform.execution_plane.flows.project_intake import run_project_intake
from agent_platform.execution_plane.flows.requirement_to_delivery import RequirementToDeliveryFlow
from agent_platform.execution_plane.flows.risk_escalation import evaluate_risk
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow
from agent_platform.execution_plane.raid import check_blocked, dependency_document, raid_document
from agent_platform.execution_plane.status_report_generator import StatusClaim, find_unsourced_claims, generate_status_report
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry, lint_directory
from agent_platform.schemas.xref_validator import validate_cross_references


PROJECT = {
    "project_id": "PRJ-001",
    "name": "Demo delivery",
    "owner": "project_manager",
    "classification": "internal",
    "goal": {
        "statement": "Ship the demo",
        "target_state": "demo accepted",
        "business_value": "validates the platform",
    },
    "constraints": ["deterministic gates", "no impersonated approvals"],
    "outcomes": [{"id": "OUT-1", "statement": "working demo"}],
}


def _approval_service():
    return ApprovalService(id_generator=SequentialIdGenerator(), clock=FixedClock())


def _write(tmp_path, artifacts: dict[str, str]):
    for rel_path, text in artifacts.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


@pytest.fixture
def compiler(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    def _make():
        ids = SequentialIdGenerator()
        return CompileSpocService(
            agent_registry=agent_registry,
            capability_registry=capability_registry,
            workflow_registry=workflow_registry,
            policy=LocalDevPolicyDecisionPoint(decision_id_generator=ids),
            clock=FixedClock(),
            id_generator=ids,
        )

    return _make


@pytest.fixture
def spoc_front_matter(fixtures_dir):
    return load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter


# -- M7.1 intake ---------------------------------------------------------

def test_intake_produces_g0_g1_artifacts():
    artifacts = run_project_intake(PROJECT, timestamp="2026-08-24T09:00:00Z")
    assert set(artifacts) == {
        "public/charter/project_charter.md",
        "public/charter/initial_constraints.md",
        "public/decisions/decision_rights.md",
    }
    assert "CHARTER-PRJ-001" in artifacts["public/charter/project_charter.md"]
    assert "DECRIGHTS-PRJ-001" in artifacts["public/decisions/decision_rights.md"]


def test_planning_baseline_produces_linked_epic_story_test(tmp_path, schema_dir):
    artifacts = run_planning_baseline(PROJECT, timestamp="2026-08-24T09:00:00Z")
    assert "public/user_stories/US-001.md" in artifacts
    assert "part_of" in artifacts["public/user_stories/US-001.md"]
    assert "tested_by" in artifacts["public/user_stories/US-001.md"]
    assert "validates" in artifacts["public/test_cases/TC-001.md"]

    # DoD: intake + planning produce valid G0-G2 artifacts passing the
    # Phase 1 validators.
    _write(tmp_path, run_project_intake(PROJECT, timestamp="2026-08-24T09:00:00Z"))
    _write(tmp_path, artifacts)

    registry = SchemaRegistry(schema_dir)
    lint_result = lint_directory(tmp_path, registry)
    assert lint_result.ok, [i.message for i in lint_result.errors]

    xref = validate_cross_references(tmp_path)
    assert xref.ok, [i.message for i in xref.issues]


# -- M7.2 requirement-to-delivery facade -----------------------------------

def test_requirement_to_delivery_facade_runs_compiled_spoc(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    ids = SequentialIdGenerator()
    event_ledger = InMemoryEventLedger()
    compile_service = CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=ids),
        clock=FixedClock(),
        id_generator=ids,
    )
    flow = ProjectExecutionFlow(
        run_state_store=InMemoryRunStateStore(),
        event_ledger=event_ledger,
        approval_gateway=InMemoryApprovalGateway(),
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=ids),
        tool_executor=FakeToolExecutor({}),
        clock=FixedClock(),
        id_generator=ids,
    )

    spoc = load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter
    workflow = RequirementToDeliveryFlow(compile_service=compile_service, flow=flow)
    state = workflow.run(
        spoc,
        project_id="PRJ-001",
        options=FlowRunOptions(originating_agent_id="a", qa_agent_id="q", test_cases=[]),
    )

    assert state.manifest.workflow_id == "requirement_to_delivery"
    assert state.manifest.spoc_id == spoc["id"]
    assert state.manifest.run_id
    assert state.status is not None


# -- M7.3 change request / risk escalation ---------------------------------

def test_scope_change_denied_without_approval():
    service = _approval_service()
    decision = evaluate_change_request(
        change_kind="scope_change", subject="WBS-PRJ-001", approval_service=service
    )
    assert decision.allowed is False
    assert decision.reason == "requires_human_approval"


def test_scope_change_allowed_with_approval_record():
    service = _approval_service()
    request = service.request("scope_budget_baseline_change", "WBS-PRJ-001")
    service.resolve(request.approval_id, approved=True)

    decision = evaluate_change_request(
        change_kind="baseline_change", subject="WBS-PRJ-001", approval_service=service
    )
    assert decision.allowed is True
    assert decision.reason == "approved"


def test_unknown_change_kind_denied():
    decision = evaluate_change_request(
        change_kind="rename", subject="WBS-PRJ-001", approval_service=_approval_service()
    )
    assert decision.allowed is False
    assert decision.reason == "unknown_change_kind:rename"


def test_critical_risk_raises_human_escalation_event():
    ledger = InMemoryEventLedger()
    result = evaluate_risk(
        {"id": "RISK-1", "severity": "critical", "summary": "blocker"},
        event_ledger=ledger,
        id_generator=SequentialIdGenerator(),
        clock=FixedClock(),
        run_id="run-1",
    )
    assert result.escalated is True
    assert [e.event_type for e in ledger.events_for_run("run-1")] == ["human_escalation"]


def test_non_critical_risk_does_not_escalate():
    ledger = InMemoryEventLedger()
    result = evaluate_risk(
        {"id": "RISK-2", "severity": "medium"},
        event_ledger=ledger,
        id_generator=SequentialIdGenerator(),
        clock=FixedClock(),
        run_id="run-1",
    )
    assert result.escalated is False
    assert ledger.events_for_run("run-1") == []


# -- M7.4 RAID / blocks gate ------------------------------------------------

def test_dependency_document_and_check_blocked():
    doc = dependency_document(
        dep_id="DEP-1", title="External API", status="open", owner="pm", blocks=["SPOC-9"]
    )
    assert "blocks" in doc
    assert "SPOC-9" in doc

    deps = {
        "DEP-1": {"status": "open", "blocks": ["SPOC-9"]},
        "DEP-2": {"status": "resolved", "blocks": ["SPOC-9"]},
    }
    assert check_blocked("SPOC-9", deps) == ["DEP-1"]
    assert check_blocked("SPOC-8", deps) == []


def test_compiler_refuses_blocked_spoc(compiler, spoc_front_matter):
    service = compiler()
    service.blocked_check = lambda spoc_id: ["DEP-1"] if spoc_id == spoc_front_matter["id"] else []
    with pytest.raises(SpocCompilationError, match="blocked by unresolved dependencies"):
        service.compile(spoc_front_matter, project_id="PRJ-001")


def test_raid_document_is_valid_okf():
    doc = raid_document(
        doc_id="RISK-7",
        doc_type="risk",
        title="A risk",
        status="open",
        owner="pm",
        classification="internal",
        body="# RISK-7\n",
        timestamp="2026-08-24T09:00:00Z",
    )
    assert doc.startswith("---\n")
    assert "type: risk" in doc


# -- M7.5 status report ------------------------------------------------------

def test_status_report_has_zero_unsourced_claims():
    claims = [
        StatusClaim("claim a", "RISK-001"),
        StatusClaim("claim b", "US-001"),
    ]
    markdown = generate_status_report(project_id="PRJ-001", report_id="SR-1", claims=claims)
    assert find_unsourced_claims(markdown) == []


def test_unsourced_claim_is_detected():
    unsourced = "# Status report\n\n## Claims\n\n- no anchor here\n"
    assert find_unsourced_claims(unsourced) == ["- no anchor here"]


def test_status_report_validates_against_baseline(tmp_path, schema_dir):
    _write(tmp_path, run_planning_baseline(PROJECT, timestamp="2026-08-24T09:00:00Z"))
    claims = [StatusClaim("risk observed", "RISK-001"), StatusClaim("story progressed", "US-001")]
    _write(
        tmp_path,
        {
            "public/status/SR-1.md": generate_status_report(
                project_id="PRJ-001", report_id="SR-1", claims=claims, timestamp="2026-08-24T09:00:00Z"
            )
        },
    )

    registry = SchemaRegistry(schema_dir)
    lint_result = lint_directory(tmp_path, registry)
    assert lint_result.ok, [i.message for i in lint_result.errors]

    xref = validate_cross_references(tmp_path)
    assert xref.ok, [i.message for i in xref.issues]


# -- M7.6 closure ------------------------------------------------------------

def test_closure_blocks_on_ownerless_risk_and_issue():
    service = _approval_service()
    result = run_project_closure(
        unresolved_risks=[{"id": "RISK-1", "owner": ""}],
        unresolved_issues=[{"id": "ISS-1", "owner": ""}],
        lessons=[],
        approval_service=service,
    )
    assert result.complete is False
    assert "risk RISK-1 has no owner" in result.blockers
    assert "issue ISS-1 has no owner" in result.blockers


def test_closure_requires_approval_for_lesson_promotion():
    service = _approval_service()
    lessons = [{"id": "LESSON-1", "promote_to_global": True}]

    blocked = run_project_closure(
        unresolved_risks=[], unresolved_issues=[], lessons=lessons, approval_service=service
    )
    assert blocked.complete is False
    assert "lesson LESSON-1 lacks promotion approval" in blocked.blockers

    request = service.request("promote_private_knowledge", "LESSON-1")
    service.resolve(request.approval_id, approved=True)

    approved = run_project_closure(
        unresolved_risks=[], unresolved_issues=[], lessons=lessons, approval_service=service
    )
    assert approved.complete is True
    assert approved.promoted_lessons == ["LESSON-1"]


def test_closure_artifact_reflects_result():
    artifact = render_closure_artifact(
        project_id="PRJ-001", result=ClosureResult(complete=False, blockers=["risk RISK-1 has no owner"])
    )
    assert "closure blocked" in artifact
    assert "risk RISK-1 has no owner" in artifact


def test_okf_front_matter_shape():
    fm = okf_front_matter(okf_id="X-1", okf_type="concept", title="X", status="draft", owner="pm")
    assert fm["schema_version"] == "okf/1.1"
    assert fm["provenance"]["created_by_type"] == "system"
    rendered = render_okf(fm, "# X\n")
    assert rendered.startswith("---\n")
    assert "# X" in rendered
    assert rendered.endswith("\n")
