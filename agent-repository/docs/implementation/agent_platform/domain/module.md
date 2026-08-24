---
schema_version: code-doc/1.0
doc_id: CODE-DOC-DOMAIN-MODULE
code_unit_id: CODE-MODULE-DOMAIN
title: agent_platform.domain
code_ref: src/agent_platform/domain/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M3.1
classification: internal
related_requirements: []
related_adrs: [ADR-013, ADR-014]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.domain`

## Purpose

Framework-independent typed models for the run/attempt identity, run
state, and run events (masterplan section 13.2, plan sections 19.2 and
22.2, ADR-014).

## Classification

Pure domain layer — the innermost layer per plan section 20.2. Must never
import CrewAI, FastAPI, SQLAlchemy, Git, any cloud SDK, or any
model-provider package.

## Responsibilities

- `ids.py`: `compute_execution_key(...)` and the `RunIdentity` value
  object implementing the six-identity model (`spoc_id`/`spoc_version`,
  `execution_key`, `run_id`, `attempt_id`, `step_id`, `child_run_id`)
  from ADR-014.
- `run.py`: `RunStatus`, `RunManifest`, `ProjectRunState`, and the nested
  models (`ArtifactRef`, `ResolvedAgent`, `CapabilityCandidate`,
  `DecisionRecord`, `ValidationResult`, `ApprovalRequest`, `CostState`,
  `RunError`).
- `events.py`: `Actor` and `RunEvent` (append-only value object).

## Explicit non-responsibilities

- No orchestration logic (that's `execution_plane`).
- No matching/compilation logic (that's `control_plane`).
- No persistence (adapters implement the ports against these models).

## Public contract

Pydantic models with `model_config = ConfigDict(extra="allow")` (state
and manifest allow forward-compatible extra fields) and, for
`RunManifest`/`RunEvent`, `frozen=True`.

## Invariants

- `ProjectRunState` holds references (`ArtifactRef`), never full
  confidential document bodies (masterplan section 13.2 note).
- `RunEvent` has no mutation API.

## State and lifecycle

Value objects; no behavior beyond `compute_execution_key`,
`RunIdentity.with_new_attempt`, `CostState.remaining/would_exceed`, and
`ProjectRunState.record_step_complete/has_completed`.

## Dependencies and dependency direction

Depends only on `pydantic` and the standard library. Everything else in
`agent_platform` depends on it (correct direction per plan section 20.2).

## Security and data-classification behavior

`ArtifactRef.classification` records a reference's classification; it is
not itself an enforcement point.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

`CostState.would_exceed` is the budget guard used by callers; it never
throws.

## Events, metrics, traces, and correlation identifiers

`RunEvent` carries `run_id`/`attempt_id`/`step_id`/`correlation_id`/
`causation_id` and `aggregate_id`/`aggregate_version` per plan section
22.2.

## Minimal usage example

```python
from agent_platform.domain.ids import compute_execution_key
key = compute_execution_key(project_id="PRJ-001", spoc_id="SPOC-1",
                            spoc_version="sha256:...", resolved_input_hashes=[],
                            workflow_id="wf", workflow_version="1.0.0",
                            policy_bundle_version="p/1.0")
```

## Linked requirements, ADRs, workflows, and schemas

ADR-013 (event authority), ADR-014 (run/attempt identity). Schemas:
`run_event.schema.json`, `spoc.schema.json`.

## Linked test cases and latest accepted evidence

Covered indirectly by `test_spoc_compiler.py`, `test_project_flow.py`,
`test_event_writer.py`, `test_run_summary.py` (all passing as of the
Phase 3 commit); no dedicated domain-only test file yet (backlog).

## Material change history

- 2026-08-24: initial implementation (Phase 3, M3.1).
