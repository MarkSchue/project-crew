-- PostgreSQL operational-state schema (masterplan section 18.1 entities,
-- plan milestone M6.2). Mirrors the SQLite schema used by
-- agent_platform.adapters.sqlite so the persistence layer is swappable.

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

-- Additional operational entities (leases, approvals, policy_decisions,
-- idempotency) are added incrementally as later milestones need them;
-- this file is the M6.2 baseline covering run state and events.
