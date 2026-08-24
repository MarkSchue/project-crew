---
schema_version: code-doc/1.0
doc_id: CODE-DOC-ADAPTERS-MODULE
code_unit_id: CODE-MODULE-ADAPTERS
title: agent_platform.adapters
code_ref: src/agent_platform/adapters/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M3.6
classification: internal
related_requirements: []
related_adrs: [ADR-003, ADR-009, ADR-012, ADR-013, ADR-016, ADR-020]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.adapters`

## Purpose

Phase 3 in-memory/local test-double adapters implementing the
`agent_platform.application.ports` Protocols (plan section 17.1: Phase 3
delivers the vertical slice "through explicit ports and test doubles").

## Responsibilities / public contract

- `persistence.py`: `InMemoryRunStateStore`, `InMemoryEventLedger`.
- `sqlite.py`: `SqliteRunStateStore`, `SqliteEventLedger` (Phase 6, M6.2)
  — durable, swappable SQLite-backed implementations of the same ports.
- `approval.py`: `InMemoryApprovalGateway` (optional `auto_approve`).
- `policy.py`: `LocalDevPolicyDecisionPoint` — the non-production-
  permissive default bundle from `DEC-INCEPTION-001`, fail-closed.
- `clock_and_ids.py`: `SystemClock`, `FixedClock`, `UuidIdGenerator`,
  `SequentialIdGenerator` (the deterministic one used by tests).
- `tool_executor.py`: `FakeToolExecutor` — deterministic test-double
  keyed by test-case id, proving the QA-gate control flow without a real
  sandbox.

## Explicit non-responsibilities

- No SQLite/PostgreSQL adapter yet (plan M3.6 lists SQLite as the
  intended local store; the in-memory adapter is the first cut).
- No real sandboxed `ToolExecutor` (a follow-up to ADR-020).
- No `GitWorkspace`/`ArtifactRepository`/`ObjectStore` adapters (Phase 4,
  ADR-006/ADR-018).

## Invariants

- `InMemoryEventLedger` is append-only (no remove/mutate method).
- `LocalDevPolicyDecisionPoint.evaluate` catches its own exceptions and
  returns `deny` (fail-closed, ADR-016).

## Dependencies and dependency direction

Depends on `agent_platform.domain` and
`agent_platform.application.ports`. Depended on by tests and (transitively)
CLI demos; nothing in `domain` depends back on adapters.

## Security and data-classification behavior

`LocalDevPolicyDecisionPoint` hard-denies
`write_to_production`/`modify_access_policy` and requires an approved
approval context for publish/PR/activation/override actions.

## Linked test cases and latest accepted evidence

Exercised by `test_project_flow.py`, `test_qa_gate.py`,
`test_event_writer.py`, `test_run_summary.py` (all passing as of the
Phase 3 commit).

## Material change history

- 2026-08-24: initial implementation (Phase 3).
