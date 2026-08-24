---
schema_version: code-doc/1.0
doc_id: CODE-DOC-STATUS-REPORT
code_unit_id: CODE-STATUS-REPORT-GENERATOR
title: status_report_generator
code_ref: src/agent_platform/execution_plane/status_report_generator.py
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M7.5
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `agent_platform.execution_plane.status_report_generator`

## Purpose

Produces an OKF `status_report` whose every claim is traced via a
`reports_on` relation (masterplan section 8.5, plan milestone M7.5).

## Responsibilities

- `StatusClaim(statement, source_ref)` — one traced claim.
- `generate_status_report(...)` — render the OKF `status_report` with one
  `reports_on` relation per claim and a `[ref: ...]` anchor in the body.
- `find_unsourced_claims(markdown)` — return claim bullets in the
  `## Claims` section that lack a `[ref: ...]` anchor; an empty list
  means the report is fully sourced (enforced by test).

## Zero-unsourced-claims guarantee

The generator only emits claims through `StatusClaim` (which requires a
`source_ref`), and `find_unsourced_claims` provides the automated check;
the DoD requires the result to be empty.

## Linked test cases and latest accepted evidence

`tests/unit/test_project_workflows.py` (`test_status_report_has_zero_unsourced_claims`,
`test_unsourced_claim_is_detected`,
`test_status_report_validates_against_baseline`), passing as of the
Phase 7 commit.
