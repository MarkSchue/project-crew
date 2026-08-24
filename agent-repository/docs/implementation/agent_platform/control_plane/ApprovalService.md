---
schema_version: code-doc/1.0
doc_id: CODE-DOC-APPROVAL-SERVICE
code_unit_id: CODE-APPROVAL-SERVICE
title: ApprovalService
code_ref: src/agent_platform/control_plane/approval_service.py#ApprovalService
unit_type: application_service
status: active
owner_role: platform_engineering
introduced_in: M5.2
classification: internal
related_requirements: []
related_adrs: [ADR-009]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `ApprovalService`

## Purpose

Owns the mandatory human-approval matrix (masterplan section 15.7) and the
durable approval-request lifecycle (`pending` -> `approved` | `rejected` |
`expired`). Approval is a first-class workflow state (ADR-009).

## Classification

Governance-critical. This is the record that gates consequential actions;
an expired or missing approval must block progress.

## Responsibilities

- `requires_approval(action)` — membership in
  `MANDATORY_APPROVAL_ACTIONS`.
- `request(action, subject)` — creates a pending request (with optional
  TTL-derived `expires_at`).
- `resolve(approval_id, approved=, reason=)` — approves/rejects, but never
  approves an expired request (marks it `expired` instead).
- `is_approved(action, subject=None)` — true only for a non-expired
  approved request; expired requests never count.

## Explicit non-responsibilities

- Does not decide *which* actions are allowed in general — that is
  `PolicyEngine`. It only tracks approval records for actions the matrix
  declares mandatory.

## Public contract

```python
service = ApprovalService(id_generator=..., clock=..., approval_ttl_seconds=None)
req = service.request("production_change", "SPOC-1")
service.resolve(req.approval_id, approved=True)
assert service.is_approved("production_change", "SPOC-1")
```

## Invariants

- An expired request can never transition to `approved`.
- `is_approved` is `True` only for an explicit non-expired approved
  record.

## Dependencies and dependency direction

Depends on `domain.run.ApprovalRequest`, the `Clock`/`IdGenerator` ports,
and `approval_matrix`. Depended on by `spoc_compiler` (M5.5 wiring) and
the execution plane.

## Linked test cases and latest accepted evidence

`tests/unit/test_approval_service.py` — one parametrized case per
mandatory action type (9), plus lifecycle/rejection/expiry (passing as of
the Phase 5 commit).

## Material change history

- 2026-08-24: initial implementation (Phase 5, M5.2).
