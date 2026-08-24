"""PostgreSQL-backed RunStateStore and EventLedger (plan milestone M6.2,
ADR-003).

Same port interface as ``agent_platform.adapters.sqlite``; the schema is
defined in ``schema.sql`` (also applied automatically on first use if the
tables do not exist). ``psycopg`` is imported lazily so this module can
be imported without the optional ``postgres`` extra installed; a store
only raises when actually constructed without a usable driver.

Verification note: the swap-in test
(``tests/unit/test_postgres_persistence.py``) is skipped unless
``TEST_POSTGRES_URL`` is set, because this environment has no live
PostgreSQL server. The SQLite-backed test suite (same flow tests) is the
run-of-record proving the port is swappable.
"""

from __future__ import annotations

import json

from agent_platform.domain.events import RunEvent
from agent_platform.domain.run import ProjectRunState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_state (
    run_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    state_json JSONB NOT NULL,
    saved_seq BIGSERIAL PRIMARY KEY,
    UNIQUE (run_id, attempt_id)
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_json JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events (run_id);
"""


def _connect(url: str):
    try:
        import psycopg  # lazy import; optional extra
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "psycopg is not installed; install the 'postgres' extra "
            "(`pip install -e .[postgres]`) to use the PostgreSQL store"
        ) from exc
    return psycopg.connect(url, autocommit=True)


def _to_json_str(value) -> str:
    # psycopg3 returns JSONB columns as Python objects; sqlite/others return
    # str. Normalize both to a JSON string for Pydantic parsing.
    return value if isinstance(value, str) else json.dumps(value)


class PostgresRunStateStore:
    def __init__(self, url: str) -> None:
        self._conn = _connect(url)
        self._conn.execute(_SCHEMA)

    def save(self, run_id: str, attempt_id: str, state: ProjectRunState) -> None:
        self._conn.execute(
            """
            INSERT INTO run_state (run_id, attempt_id, state_json) VALUES (%s, %s, %s)
            ON CONFLICT (run_id, attempt_id) DO UPDATE SET state_json = EXCLUDED.state_json
            """,
            (run_id, attempt_id, state.model_dump_json()),
        )

    def load(self, run_id: str, attempt_id: str) -> ProjectRunState | None:
        row = self._conn.execute(
            "SELECT state_json FROM run_state WHERE run_id = %s AND attempt_id = %s",
            (run_id, attempt_id),
        ).fetchone()
        if row is None:
            return None
        return ProjectRunState.model_validate_json(_to_json_str(row[0]))

    def latest_attempt_id(self, run_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT attempt_id FROM run_state WHERE run_id = %s ORDER BY saved_seq DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        return row[0] if row else None

    def delete(self, run_id: str, attempt_id: str) -> None:
        self._conn.execute(
            "DELETE FROM run_state WHERE run_id = %s AND attempt_id = %s", (run_id, attempt_id)
        )

    def list_run_ids(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT run_id FROM run_state ORDER BY run_id"
        ).fetchall()
        return [row[0] for row in rows]


class PostgresEventLedger:
    def __init__(self, url: str) -> None:
        self._conn = _connect(url)
        self._conn.execute(_SCHEMA)

    def append(self, event: RunEvent) -> None:
        self._conn.execute(
            "INSERT INTO events (event_id, run_id, event_json) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (event.event_id, event.run_id, event.model_dump_json()),
        )

    def events_for_run(self, run_id: str) -> list[RunEvent]:
        rows = self._conn.execute(
            "SELECT event_json FROM events WHERE run_id = %s ORDER BY event_id", (run_id,)
        ).fetchall()
        return [RunEvent.model_validate_json(_to_json_str(row[0])) for row in rows]

    def all_events(self) -> list[RunEvent]:
        rows = self._conn.execute("SELECT event_json FROM events ORDER BY event_id").fetchall()
        return [RunEvent.model_validate_json(_to_json_str(row[0])) for row in rows]
