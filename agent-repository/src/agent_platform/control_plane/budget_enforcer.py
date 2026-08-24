"""Budget, token, runtime, and delegation limit enforcement (masterplan
section 10.2 `constraints`, plan milestone M5.4).

Enforces the four limits declared on a SPOC's ``procedure.constraints``:

- ``max_runtime_seconds``
- ``max_delegation_depth``
- ``max_child_agent_calls``
- ``max_total_cost_usd``

Exceeding any single limit raises ``BudgetLimitExceededError`` (so the
run stops before any further side effect) and emits a
``budget_threshold_reached`` event naming the limit that was hit
(M5.4 Definition of done).
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import CostState


class BudgetLimitExceededError(Exception):
    code = "BUDGET_LIMIT_EXCEEDED"

    def __init__(self, limit_name: str, message: str):
        self.limit_name = limit_name
        self.message = message
        super().__init__(message)


@dataclass
class BudgetEnforcer:
    event_ledger: EventLedger | None = None
    clock: Clock | None = None
    id_generator: IdGenerator | None = None

    def enforce(
        self,
        *,
        run_id: str,
        attempt_id: str,
        cost_state: CostState | None = None,
        additional_cost_usd: float = 0.0,
        elapsed_seconds: int | None = None,
        delegation_depth: int | None = None,
        child_agent_calls: int | None = None,
        max_runtime_seconds: int | None = None,
        max_delegation_depth: int | None = None,
        max_child_agent_calls: int | None = None,
        max_total_cost_usd: float | None = None,
    ) -> None:
        """Check all four limits; raise on the first violation (after
        emitting a budget event, if an event ledger is configured)."""
        if cost_state is not None and max_total_cost_usd is not None:
            projected = cost_state.spent_usd + additional_cost_usd
            if projected > max_total_cost_usd:
                self._violate(
                    "max_total_cost_usd",
                    f"projected {projected:.4f} exceeds {max_total_cost_usd:.4f}",
                    run_id,
                    attempt_id,
                )

        if elapsed_seconds is not None and max_runtime_seconds is not None:
            if elapsed_seconds > max_runtime_seconds:
                self._violate(
                    "max_runtime_seconds",
                    f"elapsed {elapsed_seconds}s exceeds {max_runtime_seconds}s",
                    run_id,
                    attempt_id,
                )

        if delegation_depth is not None and max_delegation_depth is not None:
            if delegation_depth > max_delegation_depth:
                self._violate(
                    "max_delegation_depth",
                    f"depth {delegation_depth} exceeds {max_delegation_depth}",
                    run_id,
                    attempt_id,
                )

        if child_agent_calls is not None and max_child_agent_calls is not None:
            if child_agent_calls > max_child_agent_calls:
                self._violate(
                    "max_child_agent_calls",
                    f"{child_agent_calls} child calls exceed {max_child_agent_calls}",
                    run_id,
                    attempt_id,
                )

    def _violate(self, limit_name: str, message: str, run_id: str, attempt_id: str) -> None:
        if self.event_ledger is not None and self.clock is not None and self.id_generator is not None:
            self.event_ledger.append(
                RunEvent(
                    event_id=self.id_generator.new_id("evt"),
                    run_id=run_id,
                    attempt_id=attempt_id,
                    aggregate_id=run_id,
                    event_type="budget_threshold_reached",
                    timestamp=self.clock.now_iso(),
                    actor=Actor(type="system", id="budget_enforcer"),
                    payload={"limit_name": limit_name},
                )
            )
        raise BudgetLimitExceededError(limit_name, message)
