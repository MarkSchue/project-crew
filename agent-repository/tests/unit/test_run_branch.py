"""Git branch-per-run tool tests (plan milestone M4.3 Definition of done)."""

import pytest

from tools.git_tools.run_branch import (
    ProtectedBranchError,
    assert_safe_branch,
    branch_name,
    commit_message,
)


def test_branch_name_uses_work_package_and_run():
    assert branch_name("SPOC-2026-0042", "run_42") == "run/SPOC-2026-0042/run_42"


def test_commit_message_contains_spoc_and_run_ids():
    message = commit_message("SPOC-1", "run_42", "deliver auth spec")
    assert "SPOC-1" in message
    assert "run_42" in message


def test_push_to_protected_branch_is_rejected():
    with pytest.raises(ProtectedBranchError):
        assert_safe_branch("main")
    with pytest.raises(ProtectedBranchError):
        assert_safe_branch("master")


def test_run_branch_is_not_protected():
    assert_safe_branch("run/SPOC-1/run_42")  # must not raise
