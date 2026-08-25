"""Attribute-based policy engine (masterplan section 15.3, plan milestone
M5.1, ADR-007/ADR-016).

Production control-plane policy decision point. Evaluates
``evaluate(action, context)`` against the attributes in masterplan
section 15.3 (actor, project, classification, operation, path, tool,
environment, SPOC), hard-deny actions, the data-classification rules from
section 15.6, and the mandatory-approval matrix from section 15.7.

Every decision is recorded (the ``policy_decisions`` store, in-memory for
the MVP) and emitted as a ``policy_decision`` event when an event ledger
is supplied (M5.1 Definition of done). The engine fails closed: an
internal evaluation error is translated to a deny decision, never an
allow.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_platform.application.ports.clock_and_ids import IdGenerator
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.application.ports.policy_decision_point import PolicyDecision
from agent_platform.control_plane.approval_matrix import MANDATORY_APPROVAL_ACTIONS
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.telemetry.metrics import MetricsRegistry

POLICY_BUNDLE_VERSION = "policy-bundle/0.1.0"

# Actions that are denied outright, independent of classification or
# approval state (masterplan section 10.2 `prohibited_actions`; the
# same hard-denies used by the Phase 3 local-dev adapter).
HARD_DENY_ACTIONS: frozenset[str] = frozenset(
    {"write_to_production", "modify_access_policy", "modify_governance_policy"}
)


@dataclass
class PolicyEngine:
    id_generator: IdGenerator
    event_ledger: EventLedger | None = None
    bundle_version: str = POLICY_BUNDLE_VERSION
    mandatory_approval_actions: frozenset[str] = MANDATORY_APPROVAL_ACTIONS
    hard_deny_actions: frozenset[str] = HARD_DENY_ACTIONS
    decisions: list[PolicyDecision] = field(default_factory=list)
    metrics: MetricsRegistry | None = None

    def evaluate(self, *, action: str, context: dict) -> PolicyDecision:
        try:
            decision = self._decide(action, context)
        except Exception as exc:  # noqa: BLE001 - fail closed (ADR-016)
            decision = PolicyDecision(
                allowed=False,
                policy_decision_id=self.id_generator.new_id("policy"),
                policy_bundle_version=self.bundle_version,
                reason=f"policy_engine_error:{exc}",
            )

        self.decisions.append(decision)
        if not decision.allowed and self.metrics is not None:
            self.metrics.inc("policy_denial_total", labels={"action": action})
        if self.event_ledger is not None:
            self.event_ledger.append(
                RunEvent(
                    event_id=self.id_generator.new_id("evt"),
                    run_id=context.get("run_id", ""),
                    attempt_id=context.get("attempt_id", ""),
                    aggregate_id=context.get("run_id", ""),
                    event_type="policy_decision",
                    timestamp=context.get("timestamp", "1970-01-01T00:00:00Z"),
                    actor=Actor(type="system", id="policy_engine"),
                    policy_decision_id=decision.policy_decision_id,
                    payload={
                        "action": action,
                        "allowed": decision.allowed,
                        "reason": decision.reason,
                    },
                )
            )
        return decision

    def _decide(self, action: str, context: dict) -> PolicyDecision:
        decision_id = self.id_generator.new_id("policy")

        if action in self.hard_deny_actions:
            return PolicyDecision(
                allowed=False,
                policy_decision_id=decision_id,
                policy_bundle_version=self.bundle_version,
                reason=f"hard_deny:{action}",
            )

        # Data classification: deny if the requested classification is not
        # within the actor's allowed classifications (masterplan 15.6).
        classification = context.get("classification")
        allowed_classifications = context.get("allowed_classifications")
        if classification and allowed_classifications and classification not in allowed_classifications:
            return PolicyDecision(
                allowed=False,
                policy_decision_id=decision_id,
                policy_bundle_version=self.bundle_version,
                reason=f"classification_denied:{classification}",
            )

        # Mandatory-approval matrix: deny unless an approved approval
        # context is present (masterplan 15.7).
        if action in self.mandatory_approval_actions:
            if not context.get("approved"):
                return PolicyDecision(
                    allowed=False,
                    policy_decision_id=decision_id,
                    policy_bundle_version=self.bundle_version,
                    reason="requires_human_approval",
                )

        return PolicyDecision(
            allowed=True,
            policy_decision_id=decision_id,
            policy_bundle_version=self.bundle_version,
            reason="default_allow",
        )
