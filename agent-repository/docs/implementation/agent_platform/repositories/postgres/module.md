---
schema_version: code-doc/1.0
doc_id: CODE-DOC-POSTGRES-MODULE
code_unit_id: CODE-MODULE-POSTGRES
title: agent_platform.repositories.postgres
code_ref: src/agent_platform/repositories/postgres/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M6.2
classification: internal
related_requirements: []
related_adrs: [ADR-003, ADR-013]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.repositories.postgres`

## Purpose

PostgreSQL-backed `RunStateStore` and `EventLedger` implementing the same
ports as the SQLite adapters (plan milestone M6.2, ADR-003, ADR-013). The
schema (`schema.sql`) mirrors the SQLite tables so the persistence layer
is swappable behind the ports.

## Classification

Infrastructure adapter; swappable behind the `RunStateStore`/
`EventLedger` ports.

## Responsibilities / public contract

- `stores.PostgresRunStateStore(url)` / `stores.PostgresEventLedger(url)`
  — same methods as the SQLite adapters, using `psycopg` (lazy import).

## Explicit non-responsibilities

- No SQLAlchemy ORM — plain psycopg + SQL (the "or equivalent" of the
  plan's M6.2 wording).

## Verification note

The swap-in test (`tests/unit/test_postgres_persistence.py`) is skipped
unless `TEST_POSTGRES_URL` is set — this environment has no live
PostgreSQL server. The SQLite-backed flow test
(`tests/unit/test_sqlite_persistence.py`) is the run-of-record proving the
ports are swappable.

## Dependencies and dependency direction

Depends on `psycopg` (optional `postgres` extra) and `agent_platform.domain`.
Depended on by shared-deployment wiring (Phase 6+).

## Material change history

- 2026-08-24: initial implementation (Phase 6, M6.2).
