"""Documentation-as-code analyzer tests (plan section 17.8)."""

from pathlib import Path

import pytest

from agent_platform.docs.analyzer import (
    CODE_DOC_SCHEMA_VERSION,
    analyze,
    discover_units,
    load_code_docs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src" / "agent_platform"
DOCS_DIR = REPO_ROOT / "docs"


def _write_doc(docs_root: Path, rel: str, front_matter: str, body: str) -> Path:
    target = docs_root / "implementation" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"---\n{front_matter}\n---\n{body}\n", encoding="utf-8")
    return target


def _doc_fm(code_ref: str, doc_id: str = "CODE-DOC-TEST") -> str:
    return (
        f"schema_version: {CODE_DOC_SCHEMA_VERSION}\n"
        f"doc_id: {doc_id}\n"
        "code_unit_id: CODE-TEST\n"
        "title: Test\n"
        f"code_ref: {code_ref}\n"
        "unit_type: class\n"
        "status: active\n"
        "owner_role: platform_engineering\n"
        "introduced_in: M1.1\n"
        "classification: internal\n"
        "related_requirements: []\n"
        "related_adrs: []\n"
        "related_test_cases: []\n"
        'last_verified_commit: "<generated-by-ci>"\n'
    )


def test_discovery_finds_classes_and_functions_and_skips_private():
    units = discover_units(SRC_DIR, REPO_ROOT)
    refs = {u.ref for u in units}
    assert "src/agent_platform/control_plane/spoc_compiler.py#CompileSpocService" in refs
    assert "src/agent_platform/control_plane/spoc_compiler.py#SpocCompilationError" in refs
    # private helpers are discovered but not "required"
    privates = [u for u in units if u.is_private]
    assert all(u.symbol.startswith("_") for u in privates)


def test_load_code_docs_only_collects_code_docs(tmp_path):
    _write_doc(tmp_path, "x/module.md", _doc_fm("src/agent_platform/x/"), "## Purpose\n")
    (tmp_path / "implementation" / "x" / "README.md").write_text("# not a code doc\n", encoding="utf-8")
    docs = load_code_docs(tmp_path)
    assert len(docs) == 1
    assert docs[0].is_module_doc is True


def test_analyze_flags_orphaned_document(tmp_path):
    _write_doc(tmp_path, "x/Bad.md", _doc_fm("src/agent_platform/does_not_exist.py#Nope"), "## Purpose\n")
    report = analyze(SRC_DIR, tmp_path)
    assert any("orphaned document" in e for e in report.errors)


def test_analyze_flags_duplicate_doc_id(tmp_path):
    _write_doc(tmp_path, "a/A.md", _doc_fm("src/agent_platform/adapters/approval.py#InMemoryApprovalGateway", "DUP"), "## Purpose\n")
    _write_doc(tmp_path, "b/B.md", _doc_fm("src/agent_platform/adapters/approval.py#InMemoryApprovalGateway", "DUP"), "## Purpose\n")
    report = analyze(SRC_DIR, tmp_path)
    assert any("duplicate doc_id 'DUP'" in e for e in report.errors)


def test_analyze_flags_missing_front_matter_key(tmp_path):
    target = _write_doc(tmp_path, "x/Missing.md", _doc_fm("src/agent_platform/adapters/approval.py#InMemoryApprovalGateway"), "## Purpose\n")
    text = target.read_text(encoding="utf-8").replace("title: Test\n", "")
    target.write_text(text, encoding="utf-8")
    report = analyze(SRC_DIR, tmp_path)
    assert any("missing front-matter key 'title'" in e for e in report.errors)


def test_coverage_ratio_is_computed():
    report = analyze(SRC_DIR, DOCS_DIR)
    assert 0.0 <= report.coverage_ratio <= 1.0
    assert report.documented_count + len(report.undocumented) == len(report.required_units)


def test_committed_docs_are_valid():
    """Regression guard: the repository's committed code docs must pass
    validation (no orphaned documents, no duplicate ids, complete front
    matter)."""
    report = analyze(SRC_DIR, DOCS_DIR)
    assert report.ok, report.errors
    assert not report.warnings, report.warnings
