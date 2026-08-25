"""Git merge-conflict failure injection tests (masterplan section 19.2,
plan milestone M8.3)."""

import pytest

from tools.git_tools.merge import GitMergeConflictError, is_merge_conflict, merge_base_into_branch
from tools.git_tools.run_branch import ProtectedBranchError


class FakeRunner:
    """Failure-injection git runner: scripted ``run_raw`` responses."""

    def __init__(self, responses: list[tuple[int, str, str]]):
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def run_raw(self, *args: str) -> tuple[int, str, str]:
        self.calls.append(args)
        return self.responses.pop(0)


def test_is_merge_conflict_detects_markers():
    assert is_merge_conflict("Auto-merging file.txt\nCONFLICT (content): Merge conflict in file.txt")
    assert is_merge_conflict("Automatic merge failed; fix conflicts and then commit the result.")
    assert not is_merge_conflict("Updating abc123..def456\nFast-forward")


def test_merge_conflict_raises_typed_error():
    runner = FakeRunner(
        [
            (0, "", ""),  # checkout run/SPOC-1/run-1
            (1, "CONFLICT (content): Merge conflict in file.txt", ""),  # merge main
        ]
    )
    with pytest.raises(GitMergeConflictError):
        merge_base_into_branch(runner, "run/SPOC-1/run-1", "main")
    assert runner.calls == [("checkout", "run/SPOC-1/run-1"), ("merge", "main")]


def test_clean_merge_returns_output():
    runner = FakeRunner([(0, "", ""), (0, "Updating abc..def", "")])
    assert merge_base_into_branch(runner, "run/SPOC-1/run-1", "main") == "Updating abc..def"


def test_merge_refuses_protected_branch():
    runner = FakeRunner([])
    with pytest.raises(ProtectedBranchError):
        merge_base_into_branch(runner, "main", "main")
