---
schema_version: code-doc/1.0
doc_id: CODE-DOC-COMPILE-SPOC-001
code_unit_id: CODE-COMPILE-SPOC-SERVICE
title: CompileSpocService
code_ref: src/agent_platform/control_plane/spoc_compiler.py#CompileSpocService
unit_type: application_service
status: active
owner_role: platform_engineering
introduced_in: M3.2
classification: internal
related_requirements: []
related_adrs: [ADR-004, ADR-014, ADR-015]
related_test_cases: [TC-COMPILER-001, TC-COMPILER-002, TC-COMPILER-003, TC-COMPILER-004]
last_verified_commit: "<generated-by-ci>"
---

# `CompileSpocService`

## Purpose

Compiles a validated SPOC front-matter dict into an immutable
`RunManifest` (masterplan section 10.4). This is the only path into
execution: `ProjectExecutionFlow` never accepts a mutable SPOC file
directly.

## Classification

Control-plane / security-relevant: this is where capability matching,
approval-requirement derivation, and identity assignment happen before
anything is authorized to run (ADR-004).

## Responsibilities

- Parse the `workflow` reference (`"<id>@<version>"`) and resolve it
  against the `WorkflowRegistry`, rejecting unknown workflow
  id/version pairs and execution modes the workflow does not support
  (ADR-015).
- Run the deterministic capability matcher and reject compilation if any
  required capability has no agent coverage.
- Resolve primary/delegate agents into `ResolvedAgent` entries.
- Build the file allowlist from supplier inputs and output artifacts.
- Carry `procedure.constraints` (runtime/cost ceilings) into the
  manifest unchanged.
- Determine `approval_required` (classification confidential/restricted,
  any `prohibited_actions`, or an explicit policy denial).
- Compute the deterministic `execution_key` (plan section 19.2) and
  assign `run_id`/`attempt_id`/`correlation_id` via the injected
  `IdGenerator`.
- Hash the compiled manifest (excluding the hash field itself) into
  `manifest_hash`.

## Explicit non-responsibilities

- Does not validate OKF/SPOC schema structure — that is `mas project
  validate` (`agent_platform.schemas.okf_linter`), assumed to have run
  already.
- Does not read real file content to hash inputs; uses `expected_hash` if
  declared, otherwise a hash of the reference string. Real content
  hashing requires the `ArtifactRepository` port (Phase 4, ADR-018).
- Does not execute anything; produces a manifest only.

## Public contract

```python
service = CompileSpocService(
    agent_registry=..., capability_registry=..., workflow_registry=...,
    policy=..., clock=..., id_generator=...,
)
manifest: RunManifest = service.compile(spoc_front_matter_dict, project_id="PRJ-001")
```

Raises `SpocCompilationError` for: unknown workflow, unsupported
execution mode, or unresolved required capability coverage.

## Invariants

- Compiling the same SPOC twice with the same identity-generator state
  produces a byte-identical manifest (verified by
  `test_compile_is_deterministic_given_matching_id_sequence`).
- `manifest_hash` never includes itself in its own input.

## State and lifecycle

Stateless service; every `compile()` call is independent given its
injected ports.

## Concurrency and transaction assumptions

None — single-process, synchronous compilation. No shared mutable state
across calls other than the injected `IdGenerator`'s counters.

## Dependencies and dependency direction

Depends on `agent_platform.registries` (agent/capability/workflow),
`agent_platform.control_plane.capability_matcher`, `agent_platform.domain.run`,
`agent_platform.domain.ids`, `agent_platform.schemas.canonicalize`, and the
`PolicyDecisionPoint`/`Clock`/`IdGenerator` ports. Depended on by
`agent_platform.execution_plane.project_flow` (indirectly, via the
manifest it produces) and by CLI/test callers.

## Security and data-classification behavior

`approval_required` is forced `True` for `confidential`/`restricted`
classifications regardless of policy bundle content (defense in depth).

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

Fails fast: any of the three error conditions above raises before any
manifest is constructed. No partial manifest is ever returned.

## Events, metrics, traces, and correlation identifiers

Does not itself emit `RunEvent`s (no `EventLedger` dependency); the
`run_id`/`attempt_id`/`correlation_id` it assigns are what later flow
steps use to emit events.

## Minimal usage example

See "Public contract" above; see also
`tests/unit/test_spoc_compiler.py`.

## Linked requirements, ADRs, workflows, and schemas

ADR-004 (control/execution separation), ADR-014 (run/attempt identity),
ADR-015 (workflow definition split). Schema: `spoc.schema.json`.

## Linked test cases and latest accepted evidence

`tests/unit/test_spoc_compiler.py` (4 tests, all passing as of the
Phase 3 commit): manifest with split agents, determinism, unknown
workflow rejection, unsupported execution-mode rejection.

## Material change history

- 2026-08-24: initial implementation (Phase 3, M3.2).
