"""Git merge-conflict handling (masterplan section 19.2/19.3, plan
milestone M8.3).

Merging the base branch into a run branch may produce conflicts; the
conflict is detected from git output and surfaced as a typed error so the
run can dead-letter with evidence instead of silently producing a corrupt
merge. Directly merging into a protected branch remains refused
(``ProtectedBranchError``); protected-branch updates go through pull
requests (masterplan section 14.5).
"""

from __future__ import annotations

from tools.git_tools.run_branch import GitRunner, assert_safe_branch


class GitMergeConflictError(Exception):
    code = "GIT_MERGE_CONFLICT"


_CONFLICT_MARKERS = ("CONFLICT", "Automatic merge failed", "Merge conflict in")


def is_merge_conflict(output: str) -> bool:
    return any(marker in output for marker in _CONFLICT_MARKERS)


def merge_base_into_branch(runner: GitRunner, branch: str, base: str = "main") -> str:
    """Checkout `branch` and merge `base` into it. Raises
    ``GitMergeConflictError`` on conflict, ``ProtectedBranchError`` if the
    branch being operated on is protected."""
    assert_safe_branch(branch)

    code, _, err = runner.run_raw("checkout", branch)
    if code != 0:
        raise RuntimeError(f"checkout {branch} failed: {err.strip()}")

    code, stdout, stderr = runner.run_raw("merge", base)
    if is_merge_conflict(stdout + stderr):
        raise GitMergeConflictError(
            f"merging '{base}' into '{branch}' produced conflicts"
        )
    if code != 0:
        raise RuntimeError(f"merge {base} failed: {stderr.strip()}")
    return stdout.strip()
