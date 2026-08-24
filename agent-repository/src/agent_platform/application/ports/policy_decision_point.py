"""PolicyDecisionPoint port (masterplan section 15, ADR-007, ADR-016).

Fail-closed by contract: any internal error in an implementation must be
translated to a ``deny`` decision by the caller, never silently treated
as ``allow`` (ADR-016).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    policy_decision_id: str
    policy_bundle_version: str
    reason: str


class PolicyDecisionPoint(Protocol):
    def evaluate(self, *, action: str, context: dict) -> PolicyDecision: ...
