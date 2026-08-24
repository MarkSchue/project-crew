---
schema_version: code-doc/1.0
doc_id: CODE-DOC-FLOWS-MODULE
code_unit_id: CODE-MODULE-FLOWS
title: agent_platform.execution_plane.flows
code_ref: src/agent_platform/execution_plane/flows/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M7.1-M7.6
classification: internal
related_requirements: []
related_adrs: [ADR-015]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.execution_plane.flows`

## Purpose

Project-management workflow implementations for the stage gates
(masterplan section 8.2 G0-G5, plan section 12 Phase 7). These produce
and govern the G0-G5 OKF artifacts; they are the implementation side of
the workflow templates in
`project-template-repository/workflows/` (ADR-015).

## Responsibilities / public contract

- `okf_render.py`: `okf_front_matter(...)`, `render_okf(...)` — shared OKF
  rendering helper (all outputs pass `mas project validate`).
- `project_intake.py`: `run_project_intake(project, *, timestamp)` — G0/G1
  charter, initial constraints, decision rights.
- `planning_baseline.py`: `run_planning_baseline(project, *, timestamp)` —
  G2 WBS, milestone deliverable, acceptance strategy, architecture
  constraints, initial risk/dependency, and an epic with a linked,
  test-covered user story (masterplan section 9.7 traceability).
- `requirement_to_delivery.py`: `RequirementToDeliveryFlow` — the
  ``implementation.class`` of the registry workflow entry
  `requirement_to_delivery@1.2.0`; compiles a SPOC and runs
  `ProjectExecutionFlow` end-to-end (M7.2).
- `change_request.py`: `evaluate_change_request(...)` — baselined-artifact
  changes require an approval record for `scope_budget_baseline_change`
  (M7.3).
- `risk_escalation.py`: `evaluate_risk(...)` — a critical risk appends a
  `human_escalation` event to the ledger (M7.3).
- `project_closure.py`: `run_project_closure(...)` +
  `render_closure_artifact(...)` — G5 closure blocked until unresolved
  risks/issues have owners and lesson promotion is human-approved (M7.6).

## Explicit non-responsibilities

- The flows prepare evidence and artifacts but never impersonate human
  approvers (masterplan section 8.2); approvals flow through
  `ApprovalService` / `ApprovalGateway`.
- RAID logging and dependency-blocking enforcement live in
  `agent_platform.execution_plane.raid`, not here.

## Dependencies and dependency direction

Depends on `agent_platform.control_plane` (compiler, approval service),
`agent_platform.execution_plane` (flow, raid, status-report generator),
`agent_platform.domain`, and the application ports. Nothing in
`domain`/`registries` depends back.

## Security and data-classification behavior

Classification is passed through from the project record; no
classification is invented or downgraded. Mandatory-approval actions are
never auto-approved.

## Linked test cases and latest accepted evidence

`tests/unit/test_project_workflows.py` (18 tests), passing as of the
Phase 7 commit.
