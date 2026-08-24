---
schema_version: "okf/1.1"
id: "DEC-INCEPTION-001"
type: "decision"
title: "Project inception decisions"
status: "approved"
classification: "internal"
owner: "project_architect"
created_at: "2026-08-24T09:00:00Z"
updated_at: "2026-08-24T09:00:00Z"
tags: ["inception", "governance"]
source_refs:
  - "plan/crewai_multi_agent_project_masterplan.md#30-open-decisions-for-project-inception"
  - "agent-repository/docs/decisions/ADR-001.md"
  - "agent-repository/docs/decisions/ADR-002.md"
  - "agent-repository/docs/decisions/ADR-003.md"
  - "agent-repository/docs/decisions/ADR-005.md"
  - "agent-repository/docs/decisions/ADR-006.md"
  - "agent-repository/docs/decisions/ADR-016.md"
  - "agent-repository/docs/decisions/ADR-017.md"
  - "agent-repository/docs/decisions/ADR-018.md"
relations: []
provenance:
  created_by_type: "human"
  created_by_id: "project_architect"
  run_id: null
---

# Inception decisions

Answers to every bullet in masterplan section 30. Each answer is
non-deferred unless explicitly scoped to a later phase. These decisions
are inputs to ADR-001 through ADR-022 (`agent-repository/docs/decisions/`) and
must be treated as binding until superseded by a new decision record.

## Which project types are supported first?

Single-team software delivery work packages (architecture notes,
requirements analysis, documentation, code changes with tests, QA
validation) executed as bounded SPOCs. Multi-project portfolio management,
non-software projects, and fully autonomous end-to-end delivery are out of
scope for the first release (masterplan section 2.4).

## Which actions require human approval in the first deployment?

- Any output classified `confidential` or `restricted` before it leaves
  `review` state.
- Any SPOC whose `procedure.constraints` include `write_to_production`,
  `modify_access_policy`, or any entry in `prohibited_actions`.
- Any inferred (non-explicit) capability at `high_risk` threshold
  (masterplan section 12.3).
- Any Git operation that opens a pull request against a protected branch.
- Any policy exception or override of a deterministic critical failure
  (plan section 21.4).
- Creation and activation of a new agent (masterplan section 11.3, steps 8-9).

Everything else may proceed automatically inside its budget and policy
envelope, subject to QA validation (masterplan section 13.5).

## Which data classifications may be sent to which model providers?

- `public`, `internal`: any approved model provider in the model catalog.
- `confidential`: only providers explicitly flagged
  `confidential_eligible: true` in `registry/models/model_catalog.yaml`,
  with data-processing terms reviewed (ADR-022 build/reuse review covers
  this for any third-party agent platform under consideration).
- `restricted`: no model provider by default; requires an explicit,
  time-boxed policy exception approved by a human reviewer.

## Is the system local-only, on-premises, cloud-hosted, or hybrid?

Local-first for development and the first production release: a single
operator machine or on-premises host runs the control plane, execution
plane, and SQLite/PostgreSQL. Cloud-hosted shared deployment is a
Phase 6 goal (masterplan section 21 Phase 6) and is designed for but not
required for the MVP.

## Which Git platform is authoritative?

GitHub, using the three repositories already created under this account
(`agent-repository`, `project-template-repository`, and per-project
`active-project-repo` instances), with branch protection on `main`
(masterplan section 7, M0.4).

## Which identity provider and secrets manager are used?

For the local-first MVP: OS-level user identity (the operator's own
GitHub/OS account) and environment-variable-based secrets loaded from a
local `.env` file that is git-ignored and never committed. A dedicated
identity provider (OIDC/SSO) and a managed secrets store (e.g. a cloud
secrets manager or HashiCorp Vault) are deferred to Phase 6 shared
deployment, and must be resolved by ADR before any multi-user deployment.

## Which project-management system, if any, is synchronized?

None for the MVP. Requirements, epics, user stories, SPOCs, risks, and
status reports are the system of record inside `active-project-repo` as
OKF files. Synchronization with an external PM tool (Jira, Azure Boards,
Linear) is an explicitly deferred Phase 7+ capability and requires its own
ADR before implementation.

## What is the maximum allowed delegation depth and run budget?

- `max_delegation_depth`: 1 by default (a primary agent may delegate to one
  level of specialist child runs; a child run may not itself delegate
  further) unless a SPOC explicitly and narrowly raises this with human
  approval, up to a hard platform ceiling of 2.
- `max_child_agent_calls`: 5 per run by default.
- `max_total_cost_usd`: 10.00 per run by default; SPOCs may lower but not
  raise this without human approval.
- `max_runtime_seconds`: 3600 per run by default.

These are platform-enforced ceilings; individual SPOCs may only tighten
them (masterplan section 10.2 `constraints`).

## Which quality metrics are release gates?

- 100% of accepted requirements/user stories have at least one `tested_by`
  test case with a passing latest test result (masterplan section 9.7,
  section 29).
- Zero dangling or type-incompatible relations in the generated knowledge
  graph (masterplan section 29).
- Zero unresolved critical security findings (plan section 18.11).
- 100% documentation coverage for required code units on protected
  branches (plan section 17.8).
- No un-triaged flaky or quarantined critical test (plan section 18.10).
Numeric coverage/mutation/latency/cost thresholds beyond these are fixed
only after a measured baseline exists (plan section 18.11), tracked in
`agent-repository/tests/evaluation/baseline.md` (M0.5).

## Which artifacts must remain Markdown and which can be external binaries?

All governed project knowledge (requirements, epics, user stories, SPOCs,
decisions, risks, issues, dependencies, deliverable descriptions,
acceptance records, status reports, run summaries) remains OKF Markdown
(masterplan section 9.5). Only genuinely non-narrative data is external:
raw `events.jsonl`, binary artifacts (images, compiled outputs, large
datasets), checksums, and generated index/graph projections. Binary
artifacts above the Git size threshold defined in ADR-018 are stored in
object storage and referenced from Markdown via an `artifact_descriptor`
(plan section 23.2).

## What retention rules apply to prompts, outputs, events, and private workspaces?

- Accepted OKF artifacts and Git history: retained indefinitely (they are
  the project record).
- `events.jsonl` run evidence: retained for the life of the project plus a
  minimum 1-year audit window, then archived (not deleted) to cold
  storage.
- Raw prompts and full model responses: not copied into the audit event by
  default (plan section 22.3); if a debug trace is captured for
  diagnostics, it is retained for 30 days and access-restricted.
- Private agent workspaces (`private/<agent_id>/scratch`): retained for
  the life of the run plus 30 days, then purged unless referenced as
  evidence from an accepted artifact.

## Who owns each agent, capability, tool, workflow, and policy?

Recorded per-entry in the owning registry file's `owner` field
(masterplan section 11.2). For the MVP, the single project owner
(`project_architect`) is the default owner of record for every registry
entry until specific entries are reassigned. `CODEOWNERS` in
`agent-repository` must mirror this assignment once more than one
contributor is active (M0.4).
