---
schema_version: code-doc/1.0
doc_id: CODE-DOC-WORKER
code_unit_id: CODE-WORKER
title: Worker
code_ref: src/agent_platform/execution_plane/worker.py#Worker
unit_type: worker
status: active
owner_role: platform_engineering
introduced_in: M6.3
classification: internal
related_requirements: []
related_adrs: [ADR-017]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `Worker`

## Purpose

Queue-backed execution worker (masterplan section 18.3, plan milestone
M6.3, ADR-017): acquires a time-limited lease, executes the canonical
Flow, and releases the lease. Recovers expired leases left by crashed
workers by reconciling persisted state before resuming.

## Classification

Execution-plane process; runs with manifest-scoped privileges only
(ADR-004).

## Responsibilities

- `run_once(manifest, options, *, ttl_seconds)` — acquire lease, run
  `ProjectExecutionFlow.start`, release lease; returns the final
  `ProjectRunState`.
- Detect an expired lease and take it over (recovery), emitting a
  `lease_reconciliation` event listing prior completed steps before
  resuming so no irreversible action is duplicated.

## Explicit non-responsibilities

- Does not pull manifests from a queue itself — the dispatcher (the
  queue/lease table from ADR-017) hands it a manifest.
- The lease store here is the in-memory management half; the durable
  DB-backed lease table is a follow-up behind the same shape.

## Public contract

```python
worker = Worker(flow=..., lease_store=..., clock=..., owner="worker-1")
state = worker.run_once(manifest, FlowRunOptions(...), ttl_seconds=30)
```

## Invariants

- A lease is always released after `run_once`, even on failure (the
  `finally` block).
- A worker never takes over a still-active lease (raises
  `LeaseUnavailableError`).

## Dependencies and dependency direction

Depends on `ProjectExecutionFlow`, the `Clock` port, and
`InMemoryLeaseStore`. Depended on by the dispatcher (later phase) and
tests.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

Lease expiry is clock-driven; reconciliation reads `RunStateStore` for
prior side effects (`completed_steps`) and emits an audit event before
resuming.

## Linked test cases and latest accepted evidence

`tests/unit/test_worker.py` (3 tests: run+release, active-lease refusal,
expired-lease recovery with reconciliation) — passing as of the Phase 6
commit.

## Material change history

- 2026-08-24: initial implementation (Phase 6, M6.3).
