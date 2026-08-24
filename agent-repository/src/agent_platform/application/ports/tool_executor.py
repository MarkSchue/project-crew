"""Tool executor port (plan section 21.2, ADR-020).

Executes a declared, sandboxed test/tool call and returns immutable
evidence. The QA agent (Phase 3 qa_gate) consumes this evidence but never
executes tests itself (ADR-020: evidence producer/reviewer separation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_id: str
    exit_code: int
    passed: bool
    evidence: dict


class ToolExecutor(Protocol):
    def execute(self, *, tool_id: str, tool_version: str, input_payload: dict) -> ToolExecutionResult: ...
