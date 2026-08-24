import shutil
from pathlib import Path

from agent_platform.schemas.index_generator import GENERATED_MARKER, rebuild_indexes


def test_rebuild_indexes_is_idempotent(tmp_path, fixtures_dir):
    target = tmp_path / "valid"
    shutil.copytree(fixtures_dir / "okf" / "valid", target)

    first_written = rebuild_indexes(target)
    assert first_written, "expected at least one index.md to be written"

    contents_after_first_run = {p: p.read_text(encoding="utf-8") for p in first_written}

    second_written = rebuild_indexes(target)
    contents_after_second_run = {p: p.read_text(encoding="utf-8") for p in second_written}

    assert first_written == second_written
    assert contents_after_first_run == contents_after_second_run


def test_generated_index_lists_all_documents(tmp_path, fixtures_dir):
    target = tmp_path / "valid"
    shutil.copytree(fixtures_dir / "okf" / "valid", target)

    rebuild_indexes(target)
    index_text = (target / "index.md").read_text(encoding="utf-8")

    assert index_text.startswith(GENERATED_MARKER)
    assert "EPIC-100" in index_text
    assert "US-100" in index_text
    assert "TC-100" in index_text


def test_directory_without_okf_files_gets_no_index(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    written = rebuild_indexes(empty_dir)
    assert written == []
    assert not (empty_dir / "index.md").exists()
