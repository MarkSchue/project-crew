"""Deterministic ToolExecutor test-double (plan section 21.2, ADR-020).

A real production adapter runs test cases in a sandbox and produces
signed/hashed evidence. This adapter is a configurable fake: given a
mapping of ``tool_id -> ToolExecutionResult``, it deterministically
"executes" a declared test case by looking up its preconfigured result.
This is sufficient to prove the QA-gate control flow (evidence producer
vs. reviewer, masterplan section 13.5) without a real sandbox.
"""

from __future__ import annotations

import time

from agent_platform.application.ports.tool_executor import ToolExecutor, ToolExecutionResult


class TransientToolError(Exception):
    """Base class for retryable tool failures (masterplan section 19.2)."""


class ToolTimeoutError(TransientToolError):
    """A tool call that did not complete within its time budget."""


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


class RetryingToolExecutor:
    """Retry wrapper for transient tool failures (masterplan section 19.2).

    Retries only known-transient exception types with exponential backoff;
    permanent failures propagate immediately. Irreversible tool calls must
    carry an idempotency key — the ``test_case_id`` in ``input_payload``
    is that key for the QA gate's evidence producer.
    """

    def __init__(
        self,
        inner: ToolExecutor,
        *,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.05,
        sleep_fn=time.sleep,
        transient_types: tuple[type[Exception], ...] = (TransientToolError,),
    ) -> None:
        self.inner = inner
        self.max_attempts = max_attempts
        self.backoff_base_seconds = backoff_base_seconds
        self.sleep_fn = sleep_fn
        self.transient_types = transient_types

    def execute(self, *, tool_id: str, tool_version: str, input_payload: dict) -> ToolExecutionResult:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.inner.execute(tool_id=tool_id, tool_version=tool_version, input_payload=input_payload)
            except self.transient_types as exc:
                last_exc = exc
                if attempt < self.max_attempts:
                    self.sleep_fn(self.backoff_base_seconds * (2 ** (attempt - 1)))
        assert last_exc is not None
        raise last_exc
