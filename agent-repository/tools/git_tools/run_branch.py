"""Git branch-per-run tooling (masterplan section 14.5, plan milestone
M4.3).

One run uses one branch ``run/<spoc-id>/<run-id>`` (plan section 23.3
corrects this to "branch by work package, not blindly by retry attempt",
so rework attempts under the same run reuse the same branch). Agents
never push directly to protected branches; the guard here is the
client-side half of M0.4's branch protection (the server-side rule is
configured in GitHub).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PROTECTED_BRANCHES = ("main", "master")


class ProtectedBranchError(Exception):
    code = "PROTECTED_BRANCH"


def branch_name(spoc_id: str, run_id: str) -> str:
    """Branch unit for one logical run (masterplan section 14.5)."""
    return f"run/{spoc_id}/{run_id}"


def commit_message(spoc_id: str, run_id: str, summary: str) -> str:
    """Commit message that always includes the SPOC id and run id
    (masterplan section 14.5)."""
    return f"{summary}\n\nSPOC: {spoc_id}\nRun: {run_id}"


def assert_safe_branch(branch: str) -> None:
    """Reject any operation that would push/commit directly to a
    protected branch (client-side half of M0.4)."""
    if branch in PROTECTED_BRANCHES:
        raise ProtectedBranchError(
            f"refusing to operate on protected branch '{branch}'; use a run branch"
        )


class GitRunner:
    """Thin subprocess wrapper around the local ``git`` binary. The pure
    functions above (branch name, commit message, guard) are the unit
    under test; this class exists for real repository integration and is
    exercised only by the guard logic in tests."""

    def __init__(self, repo_dir: Path | str, *, git_binary: str = "git"):
        self.repo_dir = Path(repo_dir)
        self.git_binary = git_binary

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            [self.git_binary, "-C", str(self.repo_dir), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def create_branch(self, branch: str) -> str:
        assert_safe_branch(branch)
        return self._run("checkout", "-b", branch)

    def commit_all(self, message: str) -> str:
        self._run("add", "-A")
        self._run("commit", "-m", message)
        return self._run("rev-parse", "HEAD")

    def push(self, branch: str) -> None:
        assert_safe_branch(branch)
        self._run("push", "-u", "origin", branch)
