"""Checksum manifest and provenance stamping tests (plan milestone M4.4)."""

import json

from tools.validation_tools.checksum_manifest import (
    build_checksum_manifest,
    stamp_okf_provenance,
    write_checksum_manifest,
)


def test_checksum_manifest_roundtrip(tmp_path):
    artifacts = {"public/deliverables/auth_spec.md": b"# Auth spec"}
    output = write_checksum_manifest(tmp_path, "run_42", artifacts)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == "checksum-manifest/1.0"
    assert data["run_id"] == "run_42"
    entry = data["artifacts"]["public/deliverables/auth_spec.md"]
    assert entry["content_hash"].startswith("sha256:")
    assert entry["size_bytes"] == len(b"# Auth spec")


def test_build_checksum_manifest_is_deterministic():
    artifacts = {"a.md": b"x", "b.md": b"y"}
    assert build_checksum_manifest("r", artifacts) == build_checksum_manifest("r", artifacts)


def test_stamp_provenance_adds_block_when_missing():
    markdown = "---\nid: OKF-1\ntype: concept\n---\n# Body\n"
    out = stamp_okf_provenance(markdown, "run_42")
    assert "run_id: run_42" in out
    assert "# Body" in out


def test_stamp_provenance_replaces_existing_run_id():
    markdown = "---\nid: OKF-1\nprovenance:\n  run_id: null\n---\n# Body\n"
    out = stamp_okf_provenance(markdown, "run_42")
    assert "run_id: run_42" in out
    assert "run_id: null" not in out


def test_stamp_provenance_rejects_non_okf():
    import pytest

    with pytest.raises(ValueError):
        stamp_okf_provenance("# no front matter", "run_42")
