---
schema_version: code-doc/1.0
doc_id: CODE-DOC-RAID
code_unit_id: CODE-RAID
title: raid
code_ref: src/agent_platform/execution_plane/raid.py
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M7.4
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `agent_platform.execution_plane.raid`

## Purpose

RAID and decision-log tooling (masterplan section 8.4, plan milestone
M7.4): creates `public/risks`, `public/issues`, `public/dependencies`,
and `public/decisions` OKF files, and enforces the dependency ``blocks``
gate.

## Responsibilities

- `raid_document(...)` — render one RAID/decision OKF Markdown document.
- `dependency_document(...)` — render a dependency that ``blocks`` one or
  more SPOC ids (``blocks`` relations).
- `check_blocked(spoc_id, dependencies)` — return the ids of unresolved
  dependencies that ``blocks``-target `spoc_id`.

## Blocks gate

`CompileSpocService` accepts an optional `blocked_check` callable; when a
SPOC's id is targeted by an unresolved (open/in_progress/identified)
dependency, compilation raises `SpocCompilationError`, preventing
matching and execution (masterplan section 8.4).

## Linked test cases and latest accepted evidence

`tests/unit/test_project_workflows.py` (`test_dependency_document_and_check_blocked`,
`test_compiler_refuses_blocked_spoc`, `test_raid_document_is_valid_okf`),
passing as of the Phase 7 commit.
