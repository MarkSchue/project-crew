---
schema_version: code-doc/1.0
doc_id: CODE-DOC-PORTS-MODULE
code_unit_id: CODE-MODULE-PORTS
title: agent_platform.application.ports
code_ref: src/agent_platform/application/ports/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M3.3
classification: internal
related_requirements: []
related_adrs: [ADR-003, ADR-006, ADR-007, ADR-009, ADR-011, ADR-012, ADR-013, ADR-016, ADR-018, ADR-020]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.application.ports`

## Purpose

Defines the application-layer `Protocol`s from plan section 20.1. This is
the seam through which Phase 3 test doubles are replaced by production
adapters in Phases 4-6, without touching application/execution code
(plan section 17.1 binding correction).

## Classification

Application boundary. `PolicyDecisionPoint`, `ApprovalGateway`,
`ToolExecutor` are security-relevant ports (fail-closed, durable
approval, deterministic evidence respectively).

## Responsibilities / public contract

Each port is a thin `Protocol`:

- `run_state_store.RunStateStore` — save/load/latest_attempt_id/delete.
- `event_ledger.EventLedger` — append/events_for_run (append-only).
- `approval_gateway.ApprovalGateway` — request_approval/get_status/resolve.
- `policy_decision_point.PolicyDecisionPoint` — evaluate -> `PolicyDecision`
  (fail-closed by contract).
- `tool_executor.ToolExecutor` — execute -> `ToolExecutionResult`.
- `clock_and_ids.Clock` / `IdGenerator` — injected time and identifiers.
- `deferred_ports.*` — `ArtifactRepository`, `ObjectStore`, `GitWorkspace`,
  `ModelGateway`, `AgentRuntime`, `IdentityContext`, `BudgetMeter`,
  `SecretsProvider`; defined now, adapters deferred to later phases.

## Explicit non-responsibilities

No port contains an implementation. No port imports CrewAI/FastAPI/
SQLAlchemy/Git/cloud SDK/model providers.

## Dependencies and dependency direction

Depends on `agent_platform.domain` (types in signatures). Depended on by
`agent_platform.execution_plane`, `agent_platform.control_plane`, and
`agent_platform.adapters`.

## Security and data-classification behavior

`PolicyDecisionPoint` and `ApprovalGateway` carry the fail-closed and
durable-approval contracts (ADR-007, ADR-009, ADR-016);
`ToolExecutor` carries the evidence-producer contract (ADR-020).

## Linked test cases and latest accepted evidence

Indirectly exercised by `test_project_flow.py` and `test_qa_gate.py`
through the in-memory adapters (all passing as of the Phase 3 commit).

## Material change history

- 2026-08-24: initial implementation (Phase 3).
