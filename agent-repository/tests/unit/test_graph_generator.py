"""Knowledge-graph generator tests (plan milestone M9.1 Definition of
done)."""

from pathlib import Path

import pytest

from agent_platform.execution_plane.flows.planning_baseline import run_planning_baseline
from agent_platform.execution_plane.flows.project_intake import run_project_intake
from agent_platform.knowledge_graph.graph_generator import (
    GraphGenerationError,
    build_and_validate,
    generate_graph_index,
    load_style_config,
    write_graph_index,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLE_CONFIG = REPO_ROOT / "src" / "agent_platform" / "knowledge_graph" / "style_config.yaml"

PROJECT = {
    "project_id": "PRJ-001",
    "name": "Demo delivery",
    "owner": "project_manager",
    "classification": "internal",
    "goal": {"statement": "ship", "target_state": "done", "business_value": "x"},
    "constraints": [],
    "outcomes": [{"id": "OUT-1", "statement": "demo"}],
}


def _write(tmp_path, artifacts: dict[str, str]):
    for rel_path, text in artifacts.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _reference_project(tmp_path) -> Path:
    _write(tmp_path, run_project_intake(PROJECT, timestamp="2026-08-24T09:00:00Z"))
    _write(tmp_path, run_planning_baseline(PROJECT, timestamp="2026-08-24T09:00:00Z"))
    events = tmp_path / "private" / "qa_evaluator" / "runs" / "run-1" / "events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text('{"event_id":"e1","event_type":"test_case_executed"}\n', encoding="utf-8")
    return tmp_path


def test_graph_has_zero_dangling_relations_and_no_unknown_types(tmp_path):
    root = _reference_project(tmp_path)
    style = load_style_config(STYLE_CONFIG)
    index = build_and_validate(root, style)

    assert index.dangling_relations == []
    assert index.unknown_types == []
    assert {n.id for n in index.nodes} >= {"EPIC-001", "US-001", "TC-001", "RISK-001"}

    # The user story is linked to its epic and test case.
    edge_keys = {(e.type, e.source, e.target) for e in index.edges}
    assert ("part_of", "US-001", "EPIC-001") in edge_keys
    assert ("tested_by", "US-001", "TC-001") in edge_keys
    assert ("validates", "TC-001", "US-001") in edge_keys


def test_graph_regeneration_is_idempotent(tmp_path):
    root = _reference_project(tmp_path)
    style = load_style_config(STYLE_CONFIG)
    first = write_graph_index(root, style).read_text(encoding="utf-8")
    second = write_graph_index(root, style).read_text(encoding="utf-8")
    assert first == second


def test_events_jsonl_becomes_raw_event_leaf_node(tmp_path):
    root = _reference_project(tmp_path)
    style = load_style_config(STYLE_CONFIG)
    index = build_and_validate(root, style)
    raw_nodes = [n for n in index.nodes if n.type == "raw_event"]
    assert raw_nodes, "expected at least one raw_event leaf node for events.jsonl"
    assert any(n.title == "events.jsonl" for n in raw_nodes)


def test_unknown_node_type_fails(tmp_path):
    root = _reference_project(tmp_path)
    mystery = tmp_path / "public" / "plans" / "mystery.md"
    mystery.parent.mkdir(parents=True, exist_ok=True)
    mystery.write_text(
        "---\nschema_version: okf/1.1\nid: MYSTERY-1\ntype: mystery\ntitle: x\nstatus: draft\n"
        "classification: internal\nowner: pm\ncreated_at: 2026-08-24T09:00:00Z\n"
        "updated_at: 2026-08-24T09:00:00Z\ntags: []\nsource_refs: []\nrelations: []\n"
        "provenance: {created_by_type: system, created_by_id: t}\n---\n# x\n",
        encoding="utf-8",
    )
    style = load_style_config(STYLE_CONFIG)
    with pytest.raises(GraphGenerationError, match="no style entry"):
        build_and_validate(root, style)


def test_dangling_relation_fails(tmp_path):
    root = _reference_project(tmp_path)
    dangling = tmp_path / "public" / "risks" / "RISK-002.md"
    dangling.parent.mkdir(parents=True, exist_ok=True)
    dangling.write_text(
        "---\nschema_version: okf/1.1\nid: RISK-002\ntype: risk\ntitle: x\nstatus: open\n"
        "classification: internal\nowner: pm\ncreated_at: 2026-08-24T09:00:00Z\n"
        "updated_at: 2026-08-24T09:00:00Z\ntags: []\nsource_refs: []\n"
        "relations: [{type: blocks, target: DOES-NOT-EXIST}]\n"
        "provenance: {created_by_type: system, created_by_id: t}\n---\n# x\n",
        encoding="utf-8",
    )
    style = load_style_config(STYLE_CONFIG)
    with pytest.raises(GraphGenerationError, match="dangling"):
        build_and_validate(root, style)
