---
schema_version: code-doc/1.0
doc_id: CODE-DOC-EVALUATION-MODULE
code_unit_id: CODE-MODULE-EVALUATION
title: agent_platform.evaluation
code_ref: src/agent_platform/evaluation/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M8.2
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.evaluation`

## Purpose

Regression evaluation for claimed capabilities (masterplan section 20.3,
plan milestone M8.2). Datasets live under
`tests/evaluation/<capability>/dataset.yaml`; this package provides the
models, loader, and deterministic runner.

## Responsibilities / public contract

- `models.py`: `EvaluationDataset`, `EvalCase`, `EvaluationResult`.
- `loader.py`: `load_evaluation_dataset(path)` and
  `iter_evaluation_datasets(root)`.
- `runner.py`: `run_evaluation(dataset, adapter=None)` and
  `validate_case_output(...)` — checks `expected_properties`
  (dot-paths), `required_behaviors`, and `prohibited_behaviors`; returns
  a pass rate that is compared against the dataset's `minimum_pass_rate`.

## Explicit non-responsibilities

- No real model calls yet (masterplan section 28.6): golden outputs are
  validated today; a real model adapter plugs into `run_evaluation` later
  without changing the dataset contract.
- The CI blocking behavior lives in
  `tests/evaluation/test_evaluation_suite.py` (a failing capability
  dataset fails the suite, which runs on every registry change).

## Linked test cases and latest accepted evidence

`tests/evaluation/test_evaluation_suite.py` (3 tests), passing as of the
Phase 8 commit.
