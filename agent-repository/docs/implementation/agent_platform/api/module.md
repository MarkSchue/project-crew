---
schema_version: code-doc/1.0
doc_id: CODE-DOC-API-MODULE
code_unit_id: CODE-MODULE-API
title: agent_platform.api
code_ref: src/agent_platform/api/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M6.1, M6.5
classification: internal
related_requirements: []
related_adrs: [ADR-004]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.api`

## Purpose

The FastAPI control-plane REST surface (masterplan section 17.2, plan
milestone M6.1) plus SSE/RBAC (M6.5). The control plane is the only
process with registry/policy/schema access (ADR-004); it serves
validation, compilation, run lifecycle, approvals, registry listings, and
the run-event stream.

## Classification

Public trust boundary (threat model T1-T3): every endpoint authenticates a
bearer identity and enforces project scope.

## Responsibilities / public contract

- `app.py`: `create_app(deps) -> FastAPI` — routes for SPOC validate/
  compile, run start/list/get/cancel/resume/events, approvals, and
  registry listings, with idempotency keys, optimistic concurrency
  (If-Match ETag), pagination, and `X-Correlation-ID` echo.
- `auth.py`: `DevAuthProvider` + `Identity` + `dev_token`; project-scoped
  RBAC (`can_access_project`), admin bypass.
- `main.py`: `build_app()` — a fully-wired dev server
  (`uvicorn agent_platform.api.main:app`).

The committed OpenAPI spec is `docs/api/openapi.json` (regenerated with
`python -c "import json,agent_platform.api.main as m; json.dump(m.build_app().openapi(), open('docs/api/openapi.json','w'), indent=2)"`).

## Explicit non-responsibilities

- Does not execute the flow itself — it delegates to
  `ProjectExecutionFlow` via `ControlPlaneDeps.flow`.
- Does not implement the web UI/graph/chat endpoints (Phase 9/W9).
- The dev auth provider is a stand-in for OIDC (M6.1 allows this).

## Invariants

- A non-admin identity scoped to project X can never read project Y's
  resources (enforced per endpoint, verified by the RBAC test).

## Dependencies and dependency direction

Depends on `fastapi`, the control-plane services, the ports, and the
registries. Depended on by `main.py` and tests. Nothing in `domain`/
`registries` depends back on `api`.

## Security and data-classification behavior

RBAC is project-scoped; SSE and run reads load the run's
`manifest.project_id` and enforce scope before streaming.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

Idempotency keys deduplicate mutating run-starts; optimistic concurrency
(409 on stale If-Match) prevents lost updates.

## Events, metrics, traces, and correlation identifiers

`X-Correlation-ID` is echoed on every response; the run's own
`correlation_id` (from the compiled manifest) flows into the event stream.

## Linked test cases and latest accepted evidence

`tests/api/test_api.py` (9 tests: auth, 401/403, validate/compile, project
scope, idempotency, optimistic concurrency, pagination, correlation id,
SSE+RBAC) — passing as of the Phase 6 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 6, M6.1 + M6.5).
