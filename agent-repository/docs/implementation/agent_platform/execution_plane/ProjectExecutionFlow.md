---
schema_version: code-doc/1.0
doc_id: CODE-DOC-PROJECT-EXECUTION-FLOW-001
code_unit_id: CODE-PROJECT-EXECUTION-FLOW
title: ProjectExecutionFlow
code_ref: src/agent_platform/execution_plane/project_flow.py#ProjectExecutionFlow
unit_type: crewai_flow
status: active
owner_role: platform_engineering
introduced_in: M3.3
classification: internal
related_requirements: []
related_adrs: [ADR-001, ADR-004, ADR-009, ADR-011, ADR-012, ADR-014]
related_test_cases: [TC-FLOW-001, TC-FLOW-002, TC-FLOW-003, TC-FLOW-004, TC-FLOW-005]
last_verified_commit: "<generated-by-ci>"
---

# `ProjectExecutionFlow`

## Purpose

Implements the canonical run lifecycle from masterplan section 13.1 as an
explicit, resumable step sequence: load manifest, preflight policy check,
hydrate state, plan, optional human plan approval, execute, validate,
remediate, QA validation with rework loop, optional human acceptance,
stage/commit (Git, deferred), finalize summary, update indexes.

## Classification

Orchestration core; security-relevant at the approval and policy-check
steps (ADR-007, ADR-009).

## Responsibilities

- Sequence the 13 named steps, each emitting at least one `RunEvent`
  (masterplan section 16, verified by `test_end_to_end_vertical_slice_all_pass`).
- Persist `ProjectRunState` after every step via `RunStateStore`, so a
  restart resumes from the last completed step rather than re-executing
  it (plan M3.6, ADR-012).
- Route the QA gate's outcome to `specialist_review`, `rejected`
  (return to originating agent), or `dead_letter`.
- Support cooperative cancellation via `CancellationToken`, checked
  between steps.
- Support QA rework via `start_new_attempt`, which creates a new
  `attempt_id` under the same `run_id` (ADR-014) and resumes from
  `execute_bounded_crews`, preserving the plan/approval steps already
  completed.

## Explicit non-responsibilities

- **Not a CrewAI `Flow` subclass yet.** This is a documented deviation
  from ADR-001's long-term target: it is a plain-Python orchestrator
  behind the same ports (`RunStateStore`, `EventLedger`,
  `ApprovalGateway`, `PolicyDecisionPoint`, `ToolExecutor`, `Clock`,
  `IdGenerator`). Swapping in a real `crewai.Flow` subclass is a
  follow-up that should not require changing any calling code, because
  callers only depend on `start()`/`resume()`/`start_new_attempt()`.
- Does not call a real CrewAI Crew/Task/Agent — `execute_bounded_crews`
  currently just marks the manifest's declared output artifacts as
  produced (masterplan section 27: "the first vertical slice should
  prove the control model rather than maximum intelligence").
- Does not perform real Git operations (`stage_changes`,
  `create_commit_or_pull_request` are no-ops pending the Phase 4
  `GitWorkspace` adapter, ADR-006).
- Does not execute deterministic tests itself — delegates to
  `qa_validation_against_test_cases` (ADR-020).

## Public contract

- `start(manifest, options, cancellation_token=None) -> ProjectRunState`
- `resume(run_id, attempt_id, options, cancellation_token=None) -> ProjectRunState`
- `start_new_attempt(previous_state) -> ProjectRunState`

`FlowRunOptions` carries per-run knobs (originating/QA agent ids, test
cases, human-approval simulation flags, optional summary/index output
paths, max QA attempts).

## Invariants

- A step already present in `state.completed_steps` is never re-executed
  by `_run`.
- The loop stops immediately after any step that leaves the state in
  `waiting_for_human`, `blocked`, `dead_letter`, `rejected`, or
  `cancelled` (`_EARLY_EXIT_STATUSES`).
- `start_new_attempt` never mutates the previous attempt's persisted
  state; it creates and persists a new one.

## State and lifecycle

State is `ProjectRunState` (see `domain/run.py`); its lifecycle mirrors
`RunStatus`. Checkpointing after every step is the resumability mechanism
(plan M3.6 DoD: "killing the process mid-flow and restarting resumes from
the last persisted step").

## Concurrency and transaction assumptions

Single-writer per `(run_id, attempt_id)` is assumed; no locking is
implemented in the Phase 3 in-memory adapters. A production
`RunStateStore` adapter (SQLite/PostgreSQL) would need to add that.

## Dependencies and dependency direction

Depends only on the ports listed above plus
`agent_platform.execution_plane.qa_gate`,
`agent_platform.schemas.index_generator`, and
`agent_platform.telemetry.run_summary`. Depended on by CLI/test callers,
never by `agent_platform.domain` or `agent_platform.registries` (correct
dependency direction per plan section 20.2).

## Security and data-classification behavior

`human_plan_approval_if_required` and `human_acceptance_if_required` are
both skipped only when `manifest.approval_required` is `False`; the
manifest sets that flag per SPOC classification (see
`CompileSpocService`).

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

- Cancellation: checked before every step; sets status `cancelled` and
  emits `run_cancelled`. Resuming a cancelled run resets it to `running`
  (`_reset_if_cancelled`) rather than leaving it permanently stuck.
- QA rework: bounded by `FlowRunOptions.max_qa_attempts`; exhausting it
  transitions to `dead_letter` and emits `human_escalation_required`
  (never loops silently, per M3.8 DoD).

## Events, metrics, traces, and correlation identifiers

Every step calls `_emit(...)`, which appends a `RunEvent` carrying
`run_id`, `attempt_id`, `step_id`, and `aggregate_id` (the run id).

## Minimal usage example

```python
manifest = compile_service.compile(spoc_front_matter, project_id="PRJ-001")
flow = ProjectExecutionFlow(run_state_store=..., event_ledger=..., approval_gateway=...,
                             policy=..., tool_executor=..., clock=..., id_generator=...)
state = flow.start(manifest, FlowRunOptions(originating_agent_id="architecture_writer",
                                             qa_agent_id="qa_evaluator", test_cases=[...]))
```

## Linked requirements, ADRs, workflows, and schemas

ADR-001, ADR-004, ADR-009, ADR-011, ADR-012, ADR-014.

## Linked test cases and latest accepted evidence

`tests/unit/test_project_flow.py` (6 tests, all passing as of the Phase 3
commit): end-to-end pass, human-approval pause, QA rework then success,
exhausted-retries dead-letter, resume-after-interruption.

## Material change history

- 2026-08-24: initial implementation (Phase 3, M3.3).
