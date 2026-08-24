"""Run event domain model (masterplan section 16.1, plan section 22.2).

Mirrors ``project-template-repository/schemas/run_event.schema.json``.
Events are immutable once created; the ``EventLedger`` port never exposes
a mutation method, only ``append``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str  # "human" | "agent" | "system"
    id: str


class RunEvent(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: str = "run-event/1.0"
    event_id: str
    run_id: str
    attempt_id: str
    step_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    aggregate_type: str = "run"
    aggregate_id: str
    aggregate_version: int = 1
    event_type: str
    timestamp: str
    actor: Actor
    policy_decision_id: str | None = None
    classification: str = "internal"
    payload: dict = {}
    result: str = "ok"
    error_code: str | None = None
    integrity_hash: str | None = None
