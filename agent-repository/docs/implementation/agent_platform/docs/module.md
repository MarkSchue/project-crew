---
schema_version: code-doc/1.0
doc_id: CODE-DOC-DOCS-MODULE
code_unit_id: CODE-MODULE-DOCS
title: agent_platform.docs
code_ref: src/agent_platform/docs/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: "17.8"
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.docs`

## Purpose

Documentation-as-code tooling (plan section 17.8). Uses Python AST
analysis (never imports application code) to discover required code units,
map them to `docs/implementation/**` code documents via `code_ref` front
matter, validate the mapping, and report coverage.

## Responsibilities / public contract

- `analyzer.py`: `discover_units`, `load_code_docs`, `analyze(...)` ->
  `DocsReport` (errors, warnings, undocumented units, coverage ratio).
- Backs `mas docs validate` and `mas docs coverage`.

## Invariants

- Every code document resolves to a discovered unit or a real
  file/directory; orphaned documents are errors.
- Stable `doc_id` values are unique across the documentation tree.
- Coverage is `documented_required_code_units /
  discovered_required_code_units` (release branches target 1.0).

## Explicit non-responsibilities

- Does not import or execute application code (AST only).
- `scaffold`, `build`, `serve`, `link-check`, and `changed` (plan 17.8)
  are not yet implemented; `validate` and `coverage` are the
  machine-checkable core shipped first.

## Linked test cases and latest accepted evidence

`tests/unit/test_docs_analyzer.py` (7 tests), passing as of this commit.
