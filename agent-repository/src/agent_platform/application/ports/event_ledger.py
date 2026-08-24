"""EventLedger port (masterplan section 16, plan section 22.1, ADR-013).

Append-only: no update or delete method is exposed. The database ledger
is authoritative (ADR-013); a separate JSONL projector
(``agent_platform.telemetry.event_writer``) derives the portable evidence
file from whatever this port records.
"""

from __future__ import annotations

from typing import Protocol

from agent_platform.domain.events import RunEvent


class EventLedger(Protocol):
    def append(self, event: RunEvent) -> None: ...

    def events_for_run(self, run_id: str) -> list[RunEvent]: ...
