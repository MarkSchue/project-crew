---
schema_version: code-doc/1.0
doc_id: CODE-DOC-GIT-TOOLS-MODULE
code_unit_id: CODE-MODULE-GIT-TOOLS
title: tools.git_tools
code_ref: tools/git_tools/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M4.3
classification: internal
related_requirements: []
related_adrs: [ADR-006]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `tools.git_tools`

## Purpose

Git branch-per-run and pull-request tooling (masterplan section 14.5,
ADR-006). One run uses one branch `run/<spoc-id>/<run-id>`; agents never
push directly to protected branches.

## Classification

Security-relevant (governance): enforces the branch-per-run model and
blocks direct pushes to protected branches.

## Responsibilities / public contract

- `run_branch.branch_name(spoc_id, run_id) -> str`
- `run_branch.commit_message(spoc_id, run_id, summary) -> str` (always
  includes SPOC + run ids)
- `run_branch.assert_safe_branch(branch)` — raises `ProtectedBranchError`
  for `main`/`master` (client-side half of M0.4)
- `run_branch.GitRunner` — thin subprocess wrapper (`create_branch`,
  `commit_all`, `push`), each guarded by `assert_safe_branch`
- `pull_request.build_pull_request_body(...)` — Markdown PR body linking
  run summary, test results, and (optional) approval record

## Explicit non-responsibilities

- The server-side branch-protection rule (required review, status checks)
  is configured in GitHub, not here; `assert_safe_branch` is the
  client-side guard.
- No merge/conflict-resolution logic (that is plan section 23.3, a later
  `GitWorkspace` adapter concern).

## Invariants

- `assert_safe_branch` rejects `main` and `master` before any
  create/push operation.

## Dependencies and dependency direction

Stdlib `subprocess` + the `git` binary. Depended on by tests and (later)
the `GitWorkspace` adapter.

## Linked test cases and latest accepted evidence

`tests/unit/test_run_branch.py`, `tests/unit/test_pull_request.py` —
passing as of the Phase 4 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 4, M4.3).
