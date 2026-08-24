"""PostgreSQL persistence adapter swap-in test (plan milestone M6.2 DoD).

Skipped unless ``TEST_POSTGRES_URL`` is set, because this environment has
no live PostgreSQL server. When a server is available, this proves the
same port interface works against PostgreSQL (swappable persistence).
"""

import os

import pytest

from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import ProjectRunState, RunManifest, RunStatus

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"),
    reason="TEST_POSTGRES_URL not set (no live PostgreSQL server in this environment)",
)


def _manifest() -> RunManifest:
    return RunManifest(
        project_id="PRJ-001",
        spoc_id="SPOC-1",
        spoc_version="sha256:abc",
        execution_key="execkey_1",
        run_id="run_1",
        attempt_id="attempt_1",
        correlation_id="corr_1",
        workflow_id="wf",
        workflow_version="1.0.0",
    )


def test_postgres_run_state_roundtrip():
    from agent_platform.repositories.postgres.stores import PostgresRunStateStore

    store = PostgresRunStateStore(os.environ["TEST_POSTGRES_URL"])
    state = ProjectRunState(manifest=_manifest(), status=RunStatus.RUNNING)
    store.save("run_1", "attempt_1", state)
    assert store.load("run_1", "attempt_1").status == RunStatus.RUNNING
    assert "run_1" in store.list_run_ids()


def test_postgres_event_ledger_roundtrip():
    from agent_platform.repositories.postgres.stores import PostgresEventLedger

    ledger = PostgresEventLedger(os.environ["TEST_POSTGRES_URL"])
    ledger.append(
        RunEvent(
            event_id="evt_1",
            run_id="run_1",
            attempt_id="attempt_1",
            aggregate_id="run_1",
            event_type="test_event",
            timestamp="2026-08-24T09:00:00Z",
            actor=Actor(type="system", id="test"),
        )
    )
    assert [e.event_id for e in ledger.events_for_run("run_1")] == ["evt_1"]
