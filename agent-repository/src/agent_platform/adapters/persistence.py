"""In-memory RunStateStore and EventLedger adapters (plan M3.6, ADR-012,
ADR-013).

Suitable for unit tests and for the local vertical slice. A SQLite-backed
adapter satisfying the same ports is a follow-up (plan M3.6 mentions
SQLite explicitly); this module documents that as a pending item rather
than silently pretending it exists.
"""

from __future__ import annotations

from agent_platform.domain.events import RunEvent
from agent_platform.domain.run import ProjectRunState


class InMemoryRunStateStore:
    """Implements the ``RunStateStore`` port. Snapshots are stored keyed by
    ``(run_id, attempt_id)``; ``latest_attempt_id`` tracks insertion order
    per run so resume logic can find the most recent attempt."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, str], ProjectRunState] = {}
        self._attempt_order: dict[str, list[str]] = {}

    def save(self, run_id: str, attempt_id: str, state: ProjectRunState) -> None:
        key = (run_id, attempt_id)
        self._snapshots[key] = state.model_copy(deep=True)
        order = self._attempt_order.setdefault(run_id, [])
        if attempt_id not in order:
            order.append(attempt_id)

    def load(self, run_id: str, attempt_id: str) -> ProjectRunState | None:
        snapshot = self._snapshots.get((run_id, attempt_id))
        return snapshot.model_copy(deep=True) if snapshot else None

    def latest_attempt_id(self, run_id: str) -> str | None:
        order = self._attempt_order.get(run_id)
        return order[-1] if order else None

    def delete(self, run_id: str, attempt_id: str) -> None:
        self._snapshots.pop((run_id, attempt_id), None)
        order = self._attempt_order.get(run_id)
        if order and attempt_id in order:
            order.remove(attempt_id)

    def list_run_ids(self) -> list[str]:
        return sorted({run_id for (run_id, _) in self._snapshots})


class InMemoryEventLedger:
    """Implements the ``EventLedger`` port. Append-only: no method removes
    or mutates a previously appended event (masterplan section 16,
    verified by a write-once test)."""

    def __init__(self) -> None:
        self._events: list[RunEvent] = []

    def append(self, event: RunEvent) -> None:
        self._events.append(event)

    def events_for_run(self, run_id: str) -> list[RunEvent]:
        return [e for e in self._events if e.run_id == run_id]

    def all_events(self) -> list[RunEvent]:
        return list(self._events)
