"""SQLite-backed RunStateStore and EventLedger adapters (plan milestone
M6.2, ADR-003, ADR-012, ADR-013).

These implement the same ports as the in-memory adapters
(``agent_platform.adapters.persistence``), proving the persistence layer
is swappable behind ``RunStateStore``/``EventLedger``. The Phase 3 flow
tests run unchanged against these stores (see
``tests/unit/test_sqlite_persistence.py``).

The PostgreSQL counterpart lives in
``agent_platform.repositories.postgres`` and shares the same port
interface; its schema is the same relational shape as the tables here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from agent_platform.domain.events import RunEvent
from agent_platform.domain.run import ProjectRunState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_state (
    run_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    saved_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    UNIQUE (run_id, attempt_id)
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events (run_id);
"""


class SqliteRunStateStore:
    """SQLite-backed implementation of the ``RunStateStore`` port."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save(self, run_id: str, attempt_id: str, state: ProjectRunState) -> None:
        self._conn.execute(
            """
            INSERT INTO run_state (run_id, attempt_id, state_json)
            VALUES (?, ?, ?)
            ON CONFLICT (run_id, attempt_id)
            DO UPDATE SET state_json = excluded.state_json
            """,
            (run_id, attempt_id, state.model_dump_json()),
        )
        self._conn.commit()

    def load(self, run_id: str, attempt_id: str) -> ProjectRunState | None:
        row = self._conn.execute(
            "SELECT state_json FROM run_state WHERE run_id = ? AND attempt_id = ?",
            (run_id, attempt_id),
        ).fetchone()
        if row is None:
            return None
        return ProjectRunState.model_validate_json(row[0])

    def latest_attempt_id(self, run_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT attempt_id FROM run_state WHERE run_id = ? ORDER BY saved_seq DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        return row[0] if row else None

    def delete(self, run_id: str, attempt_id: str) -> None:
        self._conn.execute(
            "DELETE FROM run_state WHERE run_id = ? AND attempt_id = ?", (run_id, attempt_id)
        )
        self._conn.commit()

    def list_run_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT run_id FROM run_state ORDER BY run_id").fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self._conn.close()


class SqliteEventLedger:
    """SQLite-backed implementation of the ``EventLedger`` port. Append-
    only at the port level: no remove/mutate method is exposed."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, event: RunEvent) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO events (event_id, run_id, event_json) VALUES (?, ?, ?)",
            (event.event_id, event.run_id, event.model_dump_json()),
        )
        self._conn.commit()

    def events_for_run(self, run_id: str) -> list[RunEvent]:
        rows = self._conn.execute(
            "SELECT event_json FROM events WHERE run_id = ? ORDER BY rowid", (run_id,)
        ).fetchall()
        return [RunEvent.model_validate_json(row[0]) for row in rows]

    def all_events(self) -> list[RunEvent]:
        rows = self._conn.execute("SELECT event_json FROM events ORDER BY rowid").fetchall()
        return [RunEvent.model_validate_json(row[0]) for row in rows]

    def close(self) -> None:
        self._conn.close()
