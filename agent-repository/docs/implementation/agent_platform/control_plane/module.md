---
schema_version: code-doc/1.0
doc_id: CODE-DOC-CONTROL-PLANE-MODULE
code_unit_id: CODE-MODULE-CONTROL-PLANE
title: agent_platform.control_plane
code_ref: src/agent_platform/control_plane/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M2.3-M2.4, M3.2
classification: internal
related_requirements: []
related_adrs: [ADR-004, ADR-005]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.control_plane`

## Purpose

Control-plane logic that runs before execution: deterministic capability
matching (masterplan section 3.3, 12), governed capability inference, match
explanation, and (from Phase 3) SPOC-to-manifest compilation. Per ADR-004,
nothing in this module executes a CrewAI Flow or LLM call directly.

## Classification

Security-relevant: this is the trust boundary between "what a SPOC asks
for" and "what actually gets authorized to run" (ADR-004, ADR-007).

## Responsibilities

- `capability_matcher.py`: four-stage deterministic matching — resolve
  explicit capabilities, expand dependencies, apply hard filters, compute
  a weighted score; falls back to a primary+delegate composition when no
  single agent covers every required capability.
- `capability_inference.py`: classify LLM-proposed candidate capabilities
  into auto-added (low risk), needs-human-review (high risk), or
  rejected-unknown; never removes explicit capabilities.
- `match_explainer.py`: renders the matcher's decision as JSON and
  Markdown, accounting for 100% of the score weight and listing every
  rejected candidate's failing hard filter.
- `spoc_compiler.py` (Phase 3): compiles a validated SPOC front-matter
  dict into an immutable `RunManifest` (masterplan section 10.4).
- `policy_engine.py` (Phase 5, M5.1): attribute-based authorization
  (masterplan section 15.3) — hard-deny actions, classification checks,
  mandatory-approval matrix; records and emits every `policy_decision`.
- `approval_matrix.py` + `approval_service.py` (Phase 5, M5.2): the
  mandatory-approval matrix (masterplan section 15.7) and the durable
  approval-request lifecycle with expiry.
- `model_router.py` (Phase 5, M5.3): resolves model profiles with
  residency and classification constraints (most restrictive
  intersection).
- `budget_enforcer.py` (Phase 5, M5.4): enforces runtime, delegation
  depth, child-call, and cost limits, emitting `budget_threshold_reached`
  events on violation.

## Explicit non-responsibilities

- Does not execute tools, agents, or Flows (execution plane's job,
  ADR-004).
- Does not call a real LLM for inference; `capability_inference.py` only
  defines the `InferenceAdapter` protocol and post-processing rules — a
  real model-backed adapter is a Phase 5 model-routing concern.
- Does not enforce policy at tool-call time (Phase 4/5, ADR-007/ADR-016).

## Public contract

See `capability_matcher.match(request, agent_registry, capability_registry) -> MatchResult`,
`capability_inference.process_inferred_candidates(...) -> InferenceOutcome`,
`match_explainer.explain_match_json/markdown(result)`, and
`spoc_compiler.compile_spoc(...) -> RunManifest` (Phase 3; see its own
class-level doc).

## Invariants

- `match()` is deterministic and reproducible: identical inputs always
  produce an identical ranking and identical tie-break (lowest `agent_id`
  lexicographically).
- Inferred capabilities never override or remove explicit ones.

## Dependencies and dependency direction

Depends on `agent_platform.registries` and `agent_platform.schemas`.
Depended on by `agent_platform.execution_plane` (Phase 3) and
`agent_platform.cli`.

## Security and data-classification behavior

`classification` hard-filters agent eligibility in `capability_matcher`;
`capability_inference` gates high-risk capabilities behind human review.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

`match()` raises `UnknownCapabilityError` if a SPOC references a
capability id that does not exist in the registry, before any scoring
happens (fail fast).

## Events, metrics, traces, and correlation identifiers

None yet in this module; the compiled `RunManifest` (Phase 3) carries the
`run_id`/`correlation_id` that later flow steps use to emit events.

## Linked requirements, ADRs, workflows, and schemas

ADR-004 (control/execution plane separation), ADR-005 (deterministic
matching).

## Linked test cases and latest accepted evidence

`tests/unit/test_capability_matcher.py`, `test_capability_inference.py`,
`test_match_explainer.py` — passing as of the Phase 2 commit.

## Material change history

- 2026-08-24: matcher, inference, explainer (Phase 2).
- 2026-08-24: SPOC compiler added (Phase 3).
