"""Retrying tool executor tests (masterplan section 19.2, plan milestone
M8.3)."""

import pytest

from agent_platform.adapters.tool_executor import (
    RetryingToolExecutor,
    ToolTimeoutError,
    TransientToolError,
)
from agent_platform.application.ports.tool_executor import ToolExecutionResult


class FlakyExecutor:
    def __init__(self, failures_before_success: int, result: ToolExecutionResult):
        self.failures_before_success = failures_before_success
        self.result = result
        self.calls = 0

    def execute(self, *, tool_id, tool_version, input_payload):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise ToolTimeoutError(f"attempt {self.calls} timed out")
        return self.result


def _result(passed: bool) -> ToolExecutionResult:
    return ToolExecutionResult(tool_id="t", exit_code=0, passed=passed, evidence={})


def test_retries_transient_failure_then_succeeds():
    inner = FlakyExecutor(failures_before_success=2, result=_result(True))
    wrapper = RetryingToolExecutor(inner, max_attempts=3, sleep_fn=lambda _: None)
    result = wrapper.execute(tool_id="t", tool_version="1", input_payload={"test_case_id": "tc"})
    assert result.passed is True
    assert inner.calls == 3


def test_gives_up_after_max_attempts():
    inner = FlakyExecutor(failures_before_success=10, result=_result(True))
    wrapper = RetryingToolExecutor(inner, max_attempts=3, sleep_fn=lambda _: None)
    with pytest.raises(TransientToolError):
        wrapper.execute(tool_id="t", tool_version="1", input_payload={})
    assert inner.calls == 3


def test_permanent_errors_are_not_retried():
    class PermanentExecutor:
        def __init__(self):
            self.calls = 0

        def execute(self, *, tool_id, tool_version, input_payload):
            self.calls += 1
            raise ValueError("permanent failure")

    inner = PermanentExecutor()
    wrapper = RetryingToolExecutor(inner, max_attempts=3, sleep_fn=lambda _: None)
    with pytest.raises(ValueError):
        wrapper.execute(tool_id="t", tool_version="1", input_payload={})
    assert inner.calls == 1


def test_backoff_is_exponential():
    sleeps: list[float] = []
    inner = FlakyExecutor(failures_before_success=3, result=_result(True))
    wrapper = RetryingToolExecutor(
        inner, max_attempts=4, backoff_base_seconds=0.5, sleep_fn=sleeps.append
    )
    wrapper.execute(tool_id="t", tool_version="1", input_payload={})
    assert sleeps == [0.5, 1.0, 2.0]
