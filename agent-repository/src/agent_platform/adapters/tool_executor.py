"""Deterministic ToolExecutor test-double (plan section 21.2, ADR-020).

A real production adapter runs test cases in a sandbox and produces
signed/hashed evidence. This adapter is a configurable fake: given a
mapping of ``tool_id -> ToolExecutionResult``, it deterministically
"executes" a declared test case by looking up its preconfigured result.
This is sufficient to prove the QA-gate control flow (evidence producer
vs. reviewer, masterplan section 13.5) without a real sandbox.
"""

from __future__ import annotations

from agent_platform.application.ports.tool_executor import ToolExecutionResult


class FakeToolExecutor:
    def __init__(self, results_by_test_case: dict[str, ToolExecutionResult]) -> None:
        self._results_by_test_case = results_by_test_case

    def execute(self, *, tool_id: str, tool_version: str, input_payload: dict) -> ToolExecutionResult:
        test_case_id = input_payload.get("test_case_id")
        result = self._results_by_test_case.get(test_case_id)
        if result is None:
            return ToolExecutionResult(
                tool_id=tool_id, exit_code=1, passed=False, evidence={"reason": "no_fixture_result"}
            )
        return result
