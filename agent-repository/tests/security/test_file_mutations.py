"""File-mutation attributability test suite (plan milestone M4.5).

Asserts that every file mutation produced by a run is attributable to a
specific actor/tool/run and occurs only inside the manifest-derived
allowlist (i.e., on the run workspace, never on a protected path).
"""

import pytest

from tools.file_tools.path_guard import PathGuard, PathOutsideRootError
from tools.file_tools.repository_write_scoped import write_bytes


def _attribution():
    return {
        "actor_type": "agent",
        "actor_id": "architecture_writer@1.0.0",
        "tool_id": "repository.write_scoped@1.0.0",
        "run_id": "run_42",
        "spoc_id": "SPOC-2026-0042",
    }


def test_file_mutation_is_attributable_and_run_scoped(tmp_path):
    run_workspace = tmp_path / "run_workspace"
    run_workspace.mkdir()
    guard = PathGuard(mount_roots=(run_workspace,), allowlist={str(run_workspace): "write"})

    events = []
    target = run_workspace / "public" / "deliverables" / "spec.md"
    write_bytes(target, b"# Spec\n", guard, audit=events.append, attribution=_attribution())

    writes = [e for e in events if e["event"] == "repository_write"]
    assert len(writes) == 1
    recorded = writes[0]
    assert recorded["actor_id"] == "architecture_writer@1.0.0"
    assert recorded["tool_id"] == "repository.write_scoped@1.0.0"
    assert recorded["run_id"] == "run_42"
    assert recorded["spoc_id"] == "SPOC-2026-0042"

    # Reversibility guard: the mutation lives only under the run workspace
    # (mounted root); writing outside it is denied.
    outside = tmp_path / "main_branch_output" / "spec.md"
    outside.parent.mkdir()
    with pytest.raises(PathOutsideRootError):
        write_bytes(outside, b"# Spec\n", guard, audit=events.append, attribution=_attribution())
