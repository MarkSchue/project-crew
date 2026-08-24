"""Risk escalation flow (plan milestone M7.3, masterplan section 8.4).

A critical risk automatically raises a ``human_escalation`` event on the
append-only event ledger so a human is looped in (masterplan section
16.1). Below-critical risks are logged by the RAID tooling (M7.4) instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.domain.events import Actor, RunEvent


@dataclass(frozen=True)
class RiskEvaluation:
    escalated: bool
    reason: str


def evaluate_risk(
    risk: dict,
    *,
    event_ledger: EventLedger,
    id_generator: IdGenerator,
    clock: Clock,
    run_id: str,
) -> RiskEvaluation:
    severity = (risk.get("severity") or "medium").lower()
    if severity != "critical":
        return RiskEvaluation(False, "below_escalation_threshold")

    event = RunEvent(
        event_id=id_generator.new_id("event"),
        run_id=run_id,
        attempt_id=risk.get("attempt_id") or run_id,
        aggregate_id=risk.get("id") or "unknown",
        event_type="human_escalation",
        timestamp=clock.now_iso(),
        actor=Actor(type="system", id="risk_escalation"),
        payload={
            "risk_id": risk.get("id"),
            "severity": severity,
            "summary": risk.get("summary", ""),
        },
    )
    event_ledger.append(event)
    return RiskEvaluation(True, "critical_risk_escalated")
