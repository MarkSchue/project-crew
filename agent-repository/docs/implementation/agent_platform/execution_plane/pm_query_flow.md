---
schema_version: code-doc/1.0
doc_id: CODE-DOC-PM-QUERY-FLOW
code_unit_id: CODE-PM-QUERY-FLOW
title: PmQueryFlow
code_ref: src/agent_platform/execution_plane/pm_query_flow.py#PmQueryFlow
unit_type: class
status: active
owner_role: platform_engineering
introduced_in: M9.3
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `PmQueryFlow`

## Purpose

The standing Project Manager agent's read-only conversational query flow
(masterplan section 13.6, 11.4, plan milestone M9.3).

Step sequence: `load_session_state → authorize_query_scope →
query_graph_and_evidence → compose_grounded_answer → attach_citations →
log_chat_event → end`.

## Responsibilities

- `create_session(...)` / `get_session(...)` — session-scoped state.
- `ask(session_id, question)` — answers from the graph only; cites the
  OKF `id` of every artifact used; says so when ungrounded.

## Security and data-classification behavior

- `public`/`internal` readable by default; `confidential`/`restricted`
  denied by default (enforced locally, then via the injected policy
  decision point).
- Read-only: never writes artifacts, never mutates approvals or run
  state, and never triggers `execute_bounded_crews`.

## Linked test cases and latest accepted evidence

`tests/unit/test_pm_query_flow.py` (6 tests),
`tests/api/test_graph_chat_api.py` (6 tests), passing as of the Phase 9
commit.
