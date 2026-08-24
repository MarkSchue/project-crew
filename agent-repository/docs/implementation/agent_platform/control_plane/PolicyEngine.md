---
schema_version: code-doc/1.0
doc_id: CODE-DOC-POLICY-ENGINE
code_unit_id: CODE-POLICY-ENGINE
title: PolicyEngine
code_ref: src/agent_platform/control_plane/policy_engine.py#PolicyEngine
unit_type: application_service
status: active
owner_role: platform_engineering
introduced_in: M5.1
classification: internal
related_requirements: []
related_adrs: [ADR-007, ADR-016]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `PolicyEngine`

## Purpose

Attribute-based authorization engine (masterplan section 15.3), invoked
before every side effect, not only at run start. Implements the
`PolicyDecisionPoint` port.

## Classification

Security-critical. This is the concrete production policy engine behind
ADR-007 ("policies override prompts") and ADR-016 (fail-closed).

## Responsibilities

- Deny hard-deny actions (`write_to_production`, `modify_access_policy`,
  `modify_governance_policy`).
- Deny when the requested `classification` is outside the actor's
  `allowed_classifications` (masterplan section 15.6).
- Deny mandatory-approval actions unless `context["approved"]` is true
  (masterplan section 15.7).
- Record every decision in the `policy_decisions` store (in-memory list
  for the MVP) and emit a `policy_decision` event when an event ledger is
  configured (M5.1 DoD).
- Fail closed: an internal evaluation error becomes a deny.

## Explicit non-responsibilities

- Does not persist decisions to a database (in-memory list; the SQLite
  policy_decisions entity is a follow-up).
- Does not own the approval lifecycle — see `ApprovalService`.

## Public contract

```python
engine = PolicyEngine(id_generator=..., event_ledger=..., bundle_version="policy-bundle/0.1.0")
decision: PolicyDecision = engine.evaluate(action="production_change", context={...})
```

`POLICY_BUNDLE_VERSION` is the current policy bundle version, recorded in
every compiled manifest.

## Invariants

- `evaluate` never raises; an internal error returns
  `allowed=False` with reason `policy_engine_error:*`.
- Every decision is appended to `decisions` exactly once.

## Dependencies and dependency direction

Depends on the ports (`PolicyDecisionPoint`, `EventLedger`,
`IdGenerator`) and `approval_matrix`. Depended on by
`spoc_compiler` and (later) the execution plane.

## Linked test cases and latest accepted evidence

`tests/unit/test_policy_engine.py` (8 tests, incl. fail-closed and
event-emission) — passing as of the Phase 5 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 5, M5.1).
