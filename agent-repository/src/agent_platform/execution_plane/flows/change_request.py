"""Change-request flow (plan milestone M7.3, masterplan section 15.7).

Scope/budget/baseline changes are mandatory human-approval actions
(``approval_matrix.MANDATORY_APPROVAL_ACTIONS``). A change may not alter
a baselined plan artifact until an explicit approval record exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.control_plane.approval_service import ApprovalService

BASELINE_CHANGE_ACTIONS = ("scope_change", "budget_change", "baseline_change")


@dataclass(frozen=True)
class ChangeDecision:
    allowed: bool
    reason: str


def evaluate_change_request(
    *,
    change_kind: str,
    subject: str,
    approval_service: ApprovalService,
) -> ChangeDecision:
    """Decide whether a change to a baselined artifact is permitted.

    Only the three baselined-artifact change kinds are recognized; any of
    them requires an existing approval record for the mandatory action
    ``scope_budget_baseline_change`` before the change may be applied.
    """
    if change_kind not in BASELINE_CHANGE_ACTIONS:
        return ChangeDecision(False, f"unknown_change_kind:{change_kind}")

    if approval_service.is_approved("scope_budget_baseline_change", subject):
        return ChangeDecision(True, "approved")
    return ChangeDecision(False, "requires_human_approval")
