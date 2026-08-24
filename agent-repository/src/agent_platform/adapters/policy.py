"""Local-development PolicyDecisionPoint adapter (ADR-016).

Implements a small, explicit rule set derived from
``plan/decisions/inception_decisions.md`` (mandatory-approval list) as a
labeled, non-production-permissive default bundle. Fails closed: any
unexpected exception during evaluation is caught by ``evaluate`` itself
and turned into a ``deny`` decision, never propagated as an "allow".
"""

from __future__ import annotations

from agent_platform.application.ports.policy_decision_point import PolicyDecision

POLICY_BUNDLE_VERSION = "local-dev-policy/0.1.0"

# Actions that are always denied outright (masterplan section 10.2
# `prohibited_actions`, DEC-INCEPTION-001 mandatory-approval list).
_HARD_DENY_ACTIONS = {"write_to_production", "modify_access_policy"}

# Actions that require a resolved, approved ApprovalRequest before they
# are allowed (DEC-INCEPTION-001).
_REQUIRES_APPROVAL_ACTIONS = {
    "publish_confidential_output",
    "open_pull_request",
    "activate_agent",
    "override_policy_exception",
}


class LocalDevPolicyDecisionPoint:
    def __init__(self, *, decision_id_generator) -> None:
        self._decision_id_generator = decision_id_generator

    def evaluate(self, *, action: str, context: dict) -> PolicyDecision:
        try:
            return self._evaluate(action=action, context=context)
        except Exception as exc:  # noqa: BLE001 - fail-closed per ADR-016
            return PolicyDecision(
                allowed=False,
                policy_decision_id=self._decision_id_generator.new_id("policy"),
                policy_bundle_version=POLICY_BUNDLE_VERSION,
                reason=f"policy_engine_error:{exc}",
            )

    def _evaluate(self, *, action: str, context: dict) -> PolicyDecision:
        decision_id = self._decision_id_generator.new_id("policy")

        if action in _HARD_DENY_ACTIONS:
            return PolicyDecision(
                allowed=False,
                policy_decision_id=decision_id,
                policy_bundle_version=POLICY_BUNDLE_VERSION,
                reason=f"hard_deny:{action}",
            )

        if action in _REQUIRES_APPROVAL_ACTIONS:
            approved = bool(context.get("approved"))
            return PolicyDecision(
                allowed=approved,
                policy_decision_id=decision_id,
                policy_bundle_version=POLICY_BUNDLE_VERSION,
                reason="approved" if approved else "requires_human_approval",
            )

        return PolicyDecision(
            allowed=True,
            policy_decision_id=decision_id,
            policy_bundle_version=POLICY_BUNDLE_VERSION,
            reason="default_allow",
        )
