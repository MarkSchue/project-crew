---
schema_version: code-doc/1.0
doc_id: CODE-DOC-BUDGET-ENFORCER
code_unit_id: CODE-BUDGET-ENFORCER
title: BudgetEnforcer
code_ref: src/agent_platform/control_plane/budget_enforcer.py#BudgetEnforcer
unit_type: application_service
status: active
owner_role: platform_engineering
introduced_in: M5.4
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `BudgetEnforcer`

## Purpose

Enforces the four limits from a SPOC's `procedure.constraints`
(masterplan section 10.2): `max_runtime_seconds`,
`max_delegation_depth`, `max_child_agent_calls`, `max_total_cost_usd`.

## Classification

Runtime safety control — stops a run before any further side effect when a
limit is exceeded.

## Responsibilities

- `enforce(...)` checks all four limits and raises
  `BudgetLimitExceededError(limit_name, message)` on the first violation.
- When an event ledger is configured, emits a `budget_threshold_reached`
  event naming the limit that was hit (M5.4 DoD).

## Explicit non-responsibilities

- Does not accumulate spending over time — the caller passes a
  `CostState` snapshot and the delta.
- Does not cancel a running step mid-flight; it is checked at step/tool
  boundaries.

## Public contract

```python
enforcer = BudgetEnforcer(event_ledger=..., clock=..., id_generator=...)
enforcer.enforce(run_id=..., attempt_id=..., cost_state=..., additional_cost_usd=...,
                 elapsed_seconds=..., delegation_depth=..., child_agent_calls=...,
                 max_runtime_seconds=..., max_delegation_depth=...,
                 max_child_agent_calls=..., max_total_cost_usd=...)
```

## Invariants

- At most one violation is raised per `enforce` call (checks run in a
  fixed order: cost, runtime, depth, child calls).

## Dependencies and dependency direction

Depends on `domain.run.CostState`, `domain.events.RunEvent`, and the
`EventLedger`/`Clock`/`IdGenerator` ports. Depended on by the execution
plane.

## Linked test cases and latest accepted evidence

`tests/unit/test_budget_enforcer.py` (6 tests, incl. per-limit and event
emission) — passing as of the Phase 5 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 5, M5.4).
