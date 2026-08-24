"""Mandatory human-approval matrix (masterplan section 15.7).

The canonical list of action types that require an authenticated human
approval record before they may proceed. Shared by the approval service
(M5.2) and the policy engine (M5.1) so the two cannot drift apart.
"""

from __future__ import annotations

# One identifier per bullet in masterplan section 15.7 (nine action types).
MANDATORY_APPROVAL_ACTIONS: frozenset[str] = frozenset(
    {
        "scope_budget_baseline_change",
        "access_expansion",
        "policy_exception",
        "high_risk_inferred_capability",
        "external_communication",
        "production_change",
        "legal_regulatory_safety_financial_conclusion",
        "promote_private_knowledge",
        "activate_agent_or_tool",
    }
)
