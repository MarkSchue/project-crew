---
schema_version: code-doc/1.0
doc_id: CODE-DOC-EXECUTION-PLANE-MODULE
code_unit_id: CODE-MODULE-EXECUTION-PLANE
title: agent_platform.execution_plane
code_ref: src/agent_platform/execution_plane/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M3.3, M3.8
classification: internal
related_requirements: []
related_adrs: [ADR-001, ADR-020]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.execution_plane`

## Purpose

Execution-plane logic: the canonical run orchestrator and the QA gate
(masterplan section 13, plan section 21). Per ADR-004 this plane loads a
compiled manifest and never mutates registry or governance policy.

## Responsibilities / public contract

- `project_flow.py`: `ProjectExecutionFlow` — see its dedicated class
  document for the full contract and the documented not-a-CrewAI-Flow
  deviation.
- `qa_gate.py`: `qa_validation_against_test_cases(...)` and
  `qa_gate.qa_validation_against_test_cases` — deterministic test
  execution via the injected `ToolExecutor`, evidence review, and
  pass/rework/dead-letter routing with the originating-agent !=
  QA-agent hard assertion (ADR-020, M3.8 DoD).
- `worker.py`: `Worker` — queue-backed lease/recovery execution (M6.3);
  see `Worker.md`.
- `raid.py`: RAID/decision-log rendering and the dependency ``blocks``
  gate (M7.4); see `raid.md`.
- `status_report_generator.py`: OKF status reports with zero unsourced
  claims (M7.5); see `status_report_generator.md`.
- `pm_query_flow.py`: `PmQueryFlow` — the read-only Project Manager query
  flow (M9.3); see `pm_query_flow.md`.
- `flows/`: G0-G5 project-management workflows (M7.1-M7.6); see
  `flows/module.md`.

## Explicit non-responsibilities

- No CrewAI `Flow` subclass yet (documented deviation; see
  `ProjectExecutionFlow.md`).
- No real agent execution (`execute_bounded_crews` marks declared
  artifacts as produced; masterplan section 27 vertical-slice scope).
- No real Git operations (Phase 4 `GitWorkspace`).

## Dependencies and dependency direction

Depends on `agent_platform.domain`,
`agent_platform.application.ports`, `agent_platform.schemas`
(index_generator), `agent_platform.telemetry` (run_summary). Depended on
by CLI/test callers; nothing in `domain`/`registries` depends back.

## Security and data-classification behavior

Approval steps are skipped only when `manifest.approval_required` is
False; QA self-approval is rejected by hard assertion.

## Linked test cases and latest accepted evidence

`tests/unit/test_project_flow.py` (6 tests), `tests/unit/test_qa_gate.py`
(4 tests), all passing as of the Phase 3 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 3).
