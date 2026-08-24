---
schema_version: code-doc/1.0
doc_id: CODE-DOC-TEST-STRATEGY
code_unit_id: CODE-DOC-TEST-STRATEGY
title: Test strategy (current state)
code_ref: tests/
unit_type: documentation
status: active
owner_role: platform_engineering
introduced_in: M1.1-M3.x
classification: internal
related_requirements: []
related_adrs: [ADR-020]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Test strategy (current state)

This is an interim summary, not yet the full strategy document required by
plan section 18 (`docs/testing/strategy/test_strategy.md`,
`test_documentation_standard.md`, `environments.md`, etc., each as their
own file with per-test-case Markdown documents under `docs/testing/cases/`).
That full structure is deferred; this file records what exists today so
the gap is explicit rather than silent.

## What exists today

- A single `tests/unit/` pytest suite per phase, using plain functions
  (no per-test-case OKF documents yet, no `@pytest.mark.test_case(...)`
  markers yet).
- Fixtures under `tests/fixtures/` for valid and invalid OKF/SPOC/registry
  trees, used across the schema, registry, and matcher tests.
- No integration, security, evaluation, resilience, performance, or
  end-to-end layers yet (plan section 18.7) — these depend on Phase 3+
  runtime code that did not exist before this session.

## Current counts

- Phase 1 (schemas): 21 tests.
- Phase 2 (registries, matcher, inference, explainer, scaffold): 27 tests.
- Phase 3 (execution plane): see `tests/unit/test_project_flow.py`,
  `test_spoc_compiler.py`, `test_qa_gate.py`, `test_event_ledger.py`,
  `test_run_summary.py` and the count in the Phase 3 commit message.

## Deterministic testing vs. agentic QA (ADR-020)

All current tests are deterministic (no LLM calls). Per masterplan
execution principle 5 and ADR-020, this remains true even after Phase 3:
the QA gate's `ToolExecutor`/test-runner port is deterministic, and any
future agentic-review layer only interprets evidence it does not produce.

## Known gaps (tracked, not yet resolved)

- No CI wiring yet (plan M1.9 describes the workflow; not yet added to
  this repository).
- No per-test-case OKF documents or traceability matrix generation (plan
  section 18.9) — the code-to-test link is currently "read the test file
  next to the module it tests," not a machine-checked mapping.
- No security, evaluation, resilience, or performance test layers yet.
