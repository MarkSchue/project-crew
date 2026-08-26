"""Graph and QA traceability integrity regression tests (masterplan
section 22 Epic G/H, plan milestone M9.7 Definition of done)."""

from pathlib import Path

from agent_platform.execution_plane.flows.planning_baseline import run_planning_baseline
from agent_platform.execution_plane.flows.project_intake import run_project_intake
from agent_platform.knowledge_graph.graph_generator import build_and_validate, load_style_config
from agent_platform.schemas.canonicalize import load_okf_file

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLE_CONFIG = REPO_ROOT / "src" / "agent_platform" / "knowledge_graph" / "style_config.yaml"

PROJECT = {
    "project_id": "PRJ-001",
    "name": "Demo",
    "owner": "pm",
    "classification": "internal",
    "goal": {"statement": "ship", "target_state": "done", "business_value": "x"},
    "constraints": [],
    "outcomes": [{"id": "OUT-1", "statement": "demo"}],
}


def _write(root: Path, rel_path: str, text: str) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _reference_project(root: Path) -> Path:
    for rel, text in run_project_intake(PROJECT, timestamp="2026-08-24T09:00:00Z").items():
        _write(root, rel, text)
    baseline = run_planning_baseline(PROJECT, timestamp="2026-08-24T09:00:00Z")
    for rel, text in baseline.items():
        _write(root, rel, text)

    # Overwrite TC-001 to add a `produces` relation to the test result.
    _write(
        root,
        "public/test_cases/TC-001.md",
        "---\nschema_version: okf/1.1\nid: TC-001\ntype: test_case\ntitle: Acceptance test for US-001\n"
        "status: active\nclassification: internal\nowner: pm\ncreated_at: 2026-08-24T09:00:00Z\n"
        "updated_at: 2026-08-24T09:00:00Z\ntags: []\nsource_refs: []\n"
        "relations:\n  - type: validates\n    target: US-001\n"
        "  - type: produces\n    target: TR-1\n"
        "provenance: {created_by_type: system, created_by_id: project_workflows}\n"
        "---\n# TC-001\n\nVerifies US-001 against its acceptance criteria.\n",
    )

    # A SPOC, a passing test result, a run summary, and raw events.
    _write(
        root,
        "public/spocs/SPOC-1.md",
        "---\nschema_version: spoc/1.1\nid: SPOC-1\ntype: spoc\ntitle: S\nstatus: closed\n"
        "project_id: PRJ-001\nowner: pm\ncreated_at: 2026-08-24T09:00:00Z\n"
        "classification: internal\nworkflow: requirement_to_delivery@1.2.0\n"
        "supplier: {provided_by: product_owner, inputs: []}\n"
        "procedure: {objective: demo, explicit_capabilities: []}\n"
        "output: {artifacts: []}\nconsumer: {next_role: qa_agent}\n"
        "retry_policy: {max_attempts: 1}\n---\n# SPOC\n",
    )
    _write(
        root,
        "public/test_results/TR-1.md",
        "---\nschema_version: okf/1.1\nid: TR-1\ntype: test_result\ntitle: TR\nstatus: pass\n"
        "classification: internal\nowner: qa\ncreated_at: 2026-08-24T10:00:00Z\n"
        "updated_at: 2026-08-24T10:00:00Z\ntags: []\nsource_refs: []\n"
        "relations:\n  - type: generated_by\n    target: RUN-SUMMARY-1\n"
        "  - type: evidenced_by\n    target: events.jsonl\n"
        "provenance: {created_by_type: system, created_by_id: t}\n---\n# TR\n",
    )
    _write(
        root,
        "logs/runs/run-1/summary.md",
        "---\nschema_version: okf/1.1\nid: RUN-SUMMARY-1\ntype: run_summary\ntitle: S\nstatus: closed\n"
        "classification: internal\nowner: platform\ncreated_at: 2026-08-24T10:00:00Z\n"
        "updated_at: 2026-08-24T10:00:00Z\ntags: []\nsource_refs: []\n"
        "relations:\n  - type: generated_by\n    target: SPOC-1\n"
        "  - type: evidenced_by\n    target: events.jsonl\n"
        "provenance: {created_by_type: system, created_by_id: t}\n---\n# Summary\n",
    )
    _write(root, "logs/runs/run-1/events.jsonl", '{"event_id":"e1","event_type":"test_case_executed"}\n')
    return root


def test_graph_has_no_dangling_relations_on_reference_project(tmp_path):
    root = _reference_project(tmp_path)
    style = load_style_config(STYLE_CONFIG)
    index = build_and_validate(root, style)
    assert index.dangling_relations == []


def test_summary_links_back_to_spoc_and_forward_to_events(tmp_path):
    root = _reference_project(tmp_path)
    style = load_style_config(STYLE_CONFIG)
    index = build_and_validate(root, style)

    edges = {(e.type, e.source, e.target) for e in index.edges}
    assert ("generated_by", "RUN-SUMMARY-1", "SPOC-1") in edges
    # The run summary's `evidenced_by: events.jsonl` resolves to the raw
    # events leaf in the same directory.
    raw_events = [e.target for e in index.edges if e.source == "RUN-SUMMARY-1" and e.type == "evidenced_by"]
    assert raw_events == ["raw:logs/runs/run-1/events.jsonl"]

    # The test result also links back to the summary and forward to events.
    assert ("generated_by", "TR-1", "RUN-SUMMARY-1") in edges
    assert any(e.source == "TR-1" and e.type == "evidenced_by" and e.target == "raw:logs/runs/run-1/events.jsonl" for e in index.edges)


def test_requirement_coverage_and_pass_status_match_test_results(tmp_path):
    root = _reference_project(tmp_path)
    style = load_style_config(STYLE_CONFIG)
    index = build_and_validate(root, style)

    # US-001 is tested_by TC-001; TC-001 produces TR-1 (pass).
    tested_by = {e.source: e.target for e in index.edges if e.type == "tested_by"}
    produces = {e.source: e.target for e in index.edges if e.type == "produces"}

    assert tested_by.get("US-001") == "TC-001"
    test_cases = {tc for story, tc in tested_by.items() if story == "US-001"}
    assert test_cases == {"TC-001"}

    for tc in test_cases:
        results = [target for source, target in produces.items() if source == tc]
        assert results, f"test case {tc} has no linked test result (not covered)"

    # Pass status is read from the test_result OKF front matter.
    tr = load_okf_file(root / "public" / "test_results" / "TR-1.md")
    assert tr.front_matter["status"] == "pass"
