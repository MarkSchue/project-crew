# Implementation Plan: CrewAI Multi-Agent System for Project Delivery

**Document status:** Detailed implementation plan derived from the masterplan
**Source of truth:** `plan/crewai_multi_agent_project_masterplan.md` (all section references below point there)
**Audience:** A coding agent or software engineering team executing the build
**Primary framework:** CrewAI
**Document version:** 1.1, deep-review revision
**Date:** 2026-08-24

> **Binding revision note:** Sections 17 through 26 of this document contain corrections and implementation controls added after a detailed architecture-to-plan consistency review. Where a later section conflicts with an earlier milestone, the later section takes precedence. Before execution, milestone owners must apply the change map in section 17.3. This preserves the original milestone numbering while removing ambiguous or unsafe implementation paths.

---

## 1. Purpose and how to use this plan

The masterplan defines *what* the system is and *why* it is structured the way it is. This document defines *how* to build it: concrete milestones, ordered tasks, file and module deliverables, dependencies between them, and the tests that prove each milestone is done.

Rules for using this plan:

- Work milestone by milestone, in the given order within a phase. Cross-phase reordering is allowed only where the dependency table in section 4 permits it.
- Every milestone lists **Deliverables** (files/modules to create or change) and **Definition of done** (verifiable, testable conditions). A milestone is not complete until its Definition of done is met and its tests pass.
- Do not start a milestone whose declared dependencies are not yet done.
- Every milestone that introduces an artifact type must also produce or update: the JSON Schema, an example fixture, a validator test, and (if user-facing) a template in `project-template-repository`.
- No milestone in Phase 3 or later may be implemented against a mutable SPOC file directly; it must go through the compiler and manifest (masterplan §10.4).
- This plan does not restate rationale already covered in the masterplan; it links back to the relevant section instead.

---

## 2. Execution principles carried over from the masterplan

These constraints apply to every milestone below and are not repeated per-milestone:

1. Schemas and validators are built before LLM prompts (masterplan §28.2).
2. CrewAI is wrapped behind thin adapters so the platform is not tightly coupled to one framework version (masterplan §28.3).
3. Every tool is small, typed, independently testable, and has a contract in the tool registry (masterplan §14.1).
4. Every LLM output is treated as untrusted until deterministically validated (masterplan §28.5).
5. Fake/stub model adapters are used for the majority of automated tests; real model calls are reserved for evaluation suites (masterplan §28.6).
6. No shared mutable audit file; one append-only event stream per run (masterplan §16, §28.12).
7. Dependencies are pinned; the CrewAI version is recorded in every run manifest (masterplan §28.13).
8. All generated artifacts remain human-readable Markdown/YAML (masterplan §28.15).

---

## 3. Workstream ownership map

Each phase is executed by one primary workstream. Workstreams can run in parallel once their dependencies are satisfied (see section 4).

| Workstream | Owns | Primary phases |
|---|---|---|
| **W1 — Foundations & Schemas** | OKF/SPOC/agent/capability/tool/model schemas, linters, hashing, indexes | 0, 1 |
| **W2 — Registry & Matching** | Agent/capability/skill/tool/model/workflow registries, deterministic matcher | 2 |
| **W3 — Runtime** | CrewAI Flow, Crew/Task factories, typed state, delegate tool | 3 |
| **W4 — Security & Repository Tools** | Path security, Git tooling, secret scanning, policy engine, approvals, model routing | 4, 5 |
| **W5 — Platform & API** | FastAPI control plane, DB, queue, worker isolation, auth | 6 |
| **W6 — Project Workflows** | Intake/planning/change/risk/status/closure flows, RAID | 7 |
| **W7 — Requirements & QA** | Epic/user story/test case/test result model, QA agent, rework loop | cross-cutting, mainly 1, 2, 3, 7 |
| **W8 — Observability & Hardening** | Metrics, traces, dashboards, DR, evaluation regression | 8 |
| **W9 — Knowledge Graph & Web UI** | Graph generator, graph/chat API, web UI, Project Manager agent | cross-cutting from 1, mainly 9 |

---

## 4. Phase dependency graph

```text
Phase 0 (Foundations)
  └─> Phase 1 (Schemas & repo bootstrap)
        ├─> Phase 2 (Registry & matcher)
        │     └─> Phase 3 (CrewAI runtime)
        │           ├─> Phase 4 (Secure repo & Git tools)
        │           │     └─> Phase 5 (Policy, approvals, budgets, routing)
        │           │           └─> Phase 6 (API, worker isolation, shared deploy)
        │           │                 └─> Phase 7 (Project-management workflows)
        │           │                       └─> Phase 8 (Observability & hardening)
        │           │                             └─> Phase 9 (Web UI)
        │           └─> W7 QA rework loop (needs Phase 3 flow + Phase 2 matcher)
        └─> W9 Graph generator (needs OKF schema + relation vocabulary from Phase 1)
              └─> Phase 9 Web UI graph/chat views (needs Phase 6 API + W7 + W9 generator)
```

Practical consequence: the knowledge-graph generator (W9) and the requirements/QA schemas (W7) can be built as soon as Phase 1 lands, and kept green incrementally through every later phase, rather than deferred entirely to Phase 9. This avoids a large, risky integration at the end.

---

## 5. Phase 0 — Decisions and foundations

**Masterplan reference:** §21 Phase 0, §24 (ADRs), §30 (open decisions)

### M0.1 — Resolve open inception decisions

**Deliverables**
- `plan/decisions/inception_decisions.md` — answers to every question in masterplan §30 (project types supported first, human-approval scope, data classification × model provider matrix, deployment model, Git platform, identity/secrets provider, PM-tool sync, delegation depth/budget ceilings, release-gate quality metrics, Markdown-vs-binary policy, retention rules, ownership matrix).

**Definition of done**
- Every bullet in masterplan §30 has an explicit, non-deferred answer or an explicitly scoped "deferred to Phase N" note.

### M0.2 — Architecture decision records

**Deliverables**
- `agent-repository/docs/adr/ADR-001..ADR-010.md`, one file per decision listed in masterplan §24, using a fixed ADR template (context, decision, consequences, status, date).

**Definition of done**
- All 10 ADRs exist, are cross-linked from `plan/decisions/inception_decisions.md`, and are marked `status: accepted`.

### M0.3 — Threat model

**Deliverables**
- `agent-repository/docs/security/threat_model.md` covering the trust boundaries in masterplan §15.1, actors in §5.1, and the prompt-injection/secret-exfiltration risks in §15.4–§15.5.

**Definition of done**
- Every trust boundary in §15.1 has at least one identified threat and one mitigating control that maps to a later milestone (cross-referenced by milestone ID).

### M0.4 — Repository ownership and branch protection

**Deliverables**
- Three GitHub (or chosen platform) repositories created: `agent-repository`, `project-template-repository`, `active-project-repo` (or a project-specific instance of the latter).
- Branch protection rules on `main`: required PR review, required status checks, no force-push, no direct push for automation identities.
- `CODEOWNERS` files reflecting the ownership matrix from M0.1.

**Definition of done**
- A test push directly to `main` on any repository is rejected.
- CI status checks are required before merge (even if CI is currently a placeholder).

### M0.5 — Definition of done and evaluation baseline

**Deliverables**
- `agent-repository/docs/definition_of_done.md` (platform-level DoD, distinct from the per-SPOC DoD in masterplan §23).
- `agent-repository/tests/evaluation/baseline.md` describing the initial (possibly empty) evaluation baseline and how it will grow per capability (masterplan §20.3).

**Definition of done**
- G0 and G1 stage gates (masterplan §8.2) are formally approved against these documents.

**Phase 0 exit criteria (masterplan):** G0 and G1 approved; trust boundaries and human approval matrix agreed. ✅ when M0.1–M0.5 are done.

---

## 6. Phase 1 — Repository bootstrap and schema toolchain

**Masterplan reference:** §21 Phase 1, §7 (topology), §9 (OKF), §22 Epic A

### M1.1 — Repository skeletons

**Deliverables**
- Full directory trees for all three repositories exactly as specified in masterplan §7.1–§7.3 (empty placeholder files/`.gitkeep` where content doesn't exist yet), including the new `epics/`, `test_cases/`, `test_results/` directories (§7.2, §7.3).
- `agent-repository/pyproject.toml` and `uv.lock` pinning Python and CrewAI versions decided in M0.1.
- `active-project-repo` skeleton also published as `project_skeleton/` inside `project-template-repository` (masterplan §7.2) so `mas project init` (M1.6) can copy it.

**Definition of done**
- `tree` of each repo matches the masterplan structure; a structure-diff test (see M1.2) passes.

### M1.2 — OKF 1.1 JSON Schema

**Deliverables**
- `project-template-repository/schemas/okf.schema.json` implementing the mandatory front matter from masterplan §9.1 and the semantics in §9.2.
- `project-template-repository/schemas/relations.schema.json` enumerating the controlled relation vocabulary from §9.3, including the newer types `generated_by`, `evidenced_by`, `reports_on`, `part_of`, `tested_by`.
- Example fixtures: one valid and one invalid OKF file per `type` currently defined (`concept`, `architecture_decision`, `requirement`, `user_story`, `epic`, `test_case`, `test_result`, `spoc`, `decision`, `risk`, `issue`, `dependency`, `deliverable`, `acceptance`, `status_report`, `run_summary`).

**Definition of done**
- Schema validates all "valid" fixtures and rejects all "invalid" fixtures with actionable error messages.
- Unknown `relations[].type` values are rejected.

### M1.3 — SPOC 1.1 JSON Schema

**Deliverables**
- `project-template-repository/schemas/spoc.schema.json` implementing the full example in masterplan §10.2, including `output.acceptance_criteria[].test_case_refs`.
- Fixtures: minimal valid SPOC, SPOC with missing required input, SPOC with conflicting `retry_policy`, SPOC missing `test_case_refs` on an acceptance criterion (should be a lint warning, not necessarily a hard schema failure — decide and document in M0.1 if it's a warning or error).

**Definition of done**
- Schema round-trips the masterplan §10.2 example without modification.
- CI rejects a SPOC referencing a non-existent input path pattern (structural check, not filesystem existence, at this stage).

### M1.4 — Agent, capability, skill, tool, and model schemas

**Deliverables**
- `project-template-repository/schemas/agent.schema.json` (masterplan §11.1)
- `project-template-repository/schemas/capability.schema.json` (masterplan §12.1)
- `project-template-repository/schemas/skill.schema.json`
- `project-template-repository/schemas/tool.schema.json` (masterplan §14.1 contract fields)
- `project-template-repository/schemas/model_catalog.schema.json`
- `project-template-repository/schemas/decision.schema.json`, `risk.schema.json` (already named in §7.2, now implemented)
- `project-template-repository/schemas/run_event.schema.json` (masterplan §16.1)

**Definition of done**
- Every schema has at least one valid and one invalid fixture and passes/fails accordingly in CI.

### M1.5 — Canonical hashing and cross-reference validator

**Deliverables**
- `agent_platform/schemas/canonicalize.py` — deterministic canonicalization + `sha256` hashing per masterplan §9.2 ("hashes are calculated after canonicalization and excluded from the hash input itself").
- `agent_platform/schemas/xref_validator.py` — walks `relations`, `source_refs`, and Markdown `[]()` links, verifying targets exist and (for `relations`) that the target's declared `type` is compatible with the relation type (e.g., `tested_by` must point at a `test_case`).
- `agent_platform/schemas/okf_linter.py` — supersedes the prototype in `architecture_plan.md` §3; adds the `part_of`/`tested_by` coverage checks from masterplan §9.7 (untested user story flagged, not silently accepted).

**Definition of done**
- Linter run against Phase 1 fixtures reports zero errors on valid fixtures and the expected error set on invalid fixtures.
- A user story fixture without `tested_by` produces a specific, distinct lint code (e.g. `OKF-COVERAGE-001`).

### M1.6 — Generated directory indexes

**Deliverables**
- `agent_platform/schemas/index_generator.py` — regenerates every directory's `index.md` from front matter (masterplan §9.4), treating indexes as pure projections (never hand-edited; add a lint rule that fails CI if an `index.md` is edited outside the generator's own commit).

**Definition of done**
- Running the generator twice in a row on an unchanged tree produces a byte-identical result (idempotent).

### M1.7 — Template lock and migration metadata

**Deliverables**
- `project-template-repository/template_manifest.yaml` with a semantic version.
- `active-project-repo/template.lock` recording the pinned template version and its content hash.
- `agent_platform/migrations/` skeleton with a no-op `0001_initial.py`-style migration and a `mas project migrate` CLI stub (implemented fully in M1.9).

**Definition of done**
- A project generated from the template records the exact template version and hash it was generated from.

### M1.8 — CLI skeleton: init and validate

**Deliverables**
- `agent_platform/cli/main.py` (Typer app) implementing, at minimum:
  - `mas project init --template <version>`
  - `mas project validate`
  - `mas registry validate` (stub returning "no registry yet" until Phase 2)
  - `mas index rebuild`

**Definition of done**
- `mas project init --template <version>` produces a working `active-project-repo` skeleton from the pinned template.
- `mas project validate` runs the OKF linter, SPOC schema check, and cross-reference validator across the generated project and exits non-zero on any violation.

### M1.9 — CI wiring for schema/lint enforcement

**Deliverables**
- `.github/workflows/validate.yml` in `project-template-repository` and in the active project repo, running `mas project validate` and the migration stub on every PR.

**Definition of done**
- A PR introducing an invalid OKF file or a broken cross-reference fails CI.
- A PR introducing a valid project change passes CI.

**Phase 1 exit criteria (masterplan):** a project can be generated from a pinned template; CI rejects invalid artifacts and broken references. ✅ when M1.1–M1.9 are done.

---

## 7. Phase 2 — Registry, capability catalog, and deterministic matcher

**Masterplan reference:** §21 Phase 2, §11, §12, §22 Epic B

### M2.1 — Registry loaders

**Deliverables**
- `agent_platform/registries/agent_registry.py`, `capability_registry.py`, `skill_registry.py`, `tool_registry.py`, `model_registry.py`, `workflow_registry.py` — each loads and validates its YAML entries against the Phase 1 schemas, and exposes a typed Pydantic model.

**Definition of done**
- Loading `agent-repository/registry/` succeeds against a fixture registry with at least 3 agents, 10 capabilities (including `security.oauth2.design`, `qa.acceptance_validation`, `qa.traceability_check` from masterplan §12.1), 2 skills, 3 tools, 1 model catalog, 1 workflow.
- Loading a registry with a dangling capability reference (agent claims a capability ID that doesn't exist) fails loudly with a specific error.

### M2.2 — Registry validators and health status

**Deliverables**
- `agent_platform/registries/validators.py` — semantic version checks, deprecation/replacement metadata checks, evaluation-evidence presence checks for claimed capabilities (masterplan §11.2).
- `agent_platform/registries/health.py` — separates static definition from runtime health (pass rate vs. `minimum_pass_rate` in masterplan §11.1).
- `mas registry validate` CLI command fully implemented.

**Definition of done**
- An agent claiming a capability with no `evidence_refs` fails validation.
- An agent whose health suite pass rate is below `minimum_pass_rate` is reported as unhealthy but not removed from the registry (health is operational state, not static removal).

### M2.3 — Deterministic capability matcher

**Deliverables**
- `agent_platform/control_plane/capability_matcher.py` implementing the four-stage process from masterplan §3.3 and the hard filters + scoring formula from §12.2.
- `agent_platform/control_plane/capability_inference.py` implementing §12.3 (LLM-proposed candidates, mapped to known IDs, low-risk auto-add vs. high-risk human review, never removing explicit capabilities). Uses a **fake/stub LLM adapter** in tests per execution principle 5.

**Definition of done**
- Given the fixture registry from M2.1, a SPOC with only explicit capabilities selects a deterministic agent and score, reproducible across repeated runs (no randomness in tie-break; document the tie-break rule, e.g. lowest agent_id lexicographically).
- A SPOC needing two capabilities split across two agents produces a primary agent plus one wrapped delegate tool candidate (masterplan §3.4, §12.4), without yet executing anything (execution is Phase 3).
- An inferred high-risk capability is flagged for human approval and does not silently expand agent selection.

### M2.4 — Matching explanation report

**Deliverables**
- `agent_platform/control_plane/match_explainer.py` — renders a machine-readable (JSON) and human-readable (Markdown) explanation of why an agent was selected or rejected, including score breakdown per masterplan §12.2 scoring formula.

**Definition of done**
- For every matcher decision in the M2.3 test suite, the explanation report accounts for 100% of the score weight and lists every rejected candidate with its failing hard filter (if any).

### M2.5 — Agent scaffolding workflow

**Deliverables**
- `agent_platform/cli/agent_scaffold.py` implementing `mas agent scaffold <agent-id>` per the workflow in masterplan §11.3 (steps 1–5 automatable; steps 6–10 require human/CI gates and are represented as TODO checklist items in the generated scaffold).
- Generated scaffold includes `agent.yaml`, `prompt.md`, `tests/` directory with a placeholder evaluation fixture, and `private_knowledge/index.md`.

**Definition of done**
- Running the scaffolder produces a registry entry that fails validation until a human fills in role/goal/capabilities/evaluations (i.e., the scaffold is intentionally incomplete and validation enforces completion before activation).

**Phase 2 exit criteria (masterplan):** matching is deterministic for explicit capabilities; every selection and rejection has machine-readable reasons. ✅ when M2.1–M2.5 are done.

---

## 8. Phase 3 — CrewAI flow runtime

**Masterplan reference:** §21 Phase 3, §13, §22 Epic C, §22 Epic H (QA loop portion)

### M3.1 — Typed run state

**Deliverables**
- `agent_platform/execution_plane/state.py` implementing `ProjectRunState` and nested models (`ArtifactRef`, `ResolvedAgent`, `CapabilityCandidate`, `DecisionRecord`, `ValidationResult`, `ApprovalRequest`, `CostState`, `RunError`) exactly per masterplan §13.2.

**Definition of done**
- State (de)serializes losslessly to/from JSON for persistence and resume (needed by M3.6).
- A unit test asserts full confidential document bodies are never placed directly in state (only references), per masterplan §13.2 note.

### M3.2 — Run compiler (manifest builder)

**Deliverables**
- `agent_platform/control_plane/spoc_compiler.py` implementing the 10 compiler steps from masterplan §10.4: resolve/hash inputs, validate schema/policy, resolve workflow/template versions, expand capability dependencies, resolve agent/skill/tool/model versions, build file allowlists, compute resource limits, record approval requirements, assign run/correlation IDs, hash/sign the manifest.
- `agent_platform/schemas/manifest.schema.json` for the compiled, immutable run manifest.

**Definition of done**
- Compiling the same SPOC twice with unchanged inputs produces a byte-identical manifest except for run/correlation IDs and timestamps.
- Compiling a SPOC with a missing required input fails with `missing_dependency` (masterplan §19.1) before any execution starts.

### M3.3 — Canonical `ProjectExecutionFlow`

**Deliverables**
- `agent_platform/execution_plane/project_flow.py` — a CrewAI `Flow` implementing every step in masterplan §13.1 as an explicit method/state transition:
  `load_run_manifest → preflight_policy_check → hydrate_typed_state → create_execution_plan → human_plan_approval_if_required → execute_bounded_crews → validate_outputs → remediate_if_allowed → qa_validation_against_test_cases → [pass] specialist_review / [fail] return_to_originating_agent → human_acceptance_if_required → stage_changes → create_commit_or_pull_request → finalize_run_summary → update_project_indexes → end`.
- Each step is a small, independently unit-testable function; the Flow wiring itself is covered by flow-transition tests (masterplan §20.1 item 4).

**Definition of done**
- A flow-transition test suite exercises every edge in the diagram above, including the `qa fail → retry` loop and the `human_plan_approval_if_required` branch both taken and skipped.

### M3.4 — Crew and Task factories

**Deliverables**
- `agent_platform/execution_plane/crew_factory.py`, `task_factory.py` — build CrewAI `Crew`/`Task` objects from the resolved manifest, enforcing the task design rules in masterplan §13.3 (one objective, required context refs, expected structured output, acceptance criteria, tool allowlist, resource limits, failure behavior, provenance).

**Definition of done**
- A task built without an expected structured output or without a tool allowlist fails factory-time validation (fail fast, before any LLM call).

### M3.5 — Controlled delegate tool

**Deliverables**
- `agent_platform/execution_plane/delegate_tool.py` implementing `AgentDelegateTool` with the strict limits from masterplan §3.4: max delegation depth, max child calls, allowed capability list, explicit I/O schema, independent run IDs, budget/token ceilings, no implicit file access, full parent-child audit linkage.

**Definition of done**
- A delegation chain exceeding `max_delegation_depth` (SPOC `constraints.max_delegation_depth`, masterplan §10.2) is rejected with a specific error before the child call is made.
- Every delegate call produces a child run ID linked to the parent run ID in the event stream (verified against M3.7).

### M3.6 — Local state store, cancellation, and resume

**Deliverables**
- `agent_platform/execution_plane/local_store.py` — SQLite-backed persistence of `ProjectRunState` snapshots keyed by `run_id`, sufficient for local dev (masterplan §3.2, §18.1 subset).
- Cancellation token plumbing per masterplan §18.4 (cooperative check between flow steps).

**Definition of done**
- Killing the process mid-flow and restarting resumes from the last persisted step without re-executing already-completed steps (masterplan §19.3).
- A cancellation request between steps stops the flow before the next tool call; a cancellation request during a non-cancellable tool call transitions the run to `cancelling` until the call returns.

### M3.7 — Structured event logging (JSONL)

**Deliverables**
- `agent_platform/telemetry/event_writer.py` — append-only JSONL writer implementing the schema in masterplan §16.1 and emitting every mandatory event type in §16.2 (including the QA-specific ones: test case executed, test result recorded, QA review passed/rejected with target agent).

**Definition of done**
- Every flow step in M3.3 emits at least one structured event; a coverage test asserts no flow step is silent.
- Events are never rewritten after being appended (enforced by an append-only file mode / write-once check in tests).

### M3.8 — QA agent role and rework loop (first runtime cut)

**Deliverables**
- `agent_platform/execution_plane/qa_gate.py` implementing `qa_validation_against_test_cases` per masterplan §13.5: QA agent selected via matcher (distinct actor from the originating agent — enforce this as a hard check, not a convention), executes/evaluates each linked test case, writes one `test_result` OKF file per test case with `produces`/`evidenced_by`/`generated_by` relations, and either advances to `specialist_review` or triggers `return_to_originating_agent` bounded by `retry_policy.max_attempts`.
- `agent_platform/schemas/test_result.schema.json` (if not already covered generically by `okf.schema.json` + a `type: test_result` profile).

**Definition of done**
- A fixture SPOC with two acceptance criteria, one intentionally failing test case: the flow produces one `pass` and one `fail` test result, rejects the SPOC, returns it to the originating agent, and a second attempt with a corrected artifact passes.
- Exhausting `retry_policy.max_attempts` with a persistent failure transitions the SPOC to `blocked`/`dead_letter` (masterplan §10.3, §19) and raises a human escalation event rather than looping.
- A single-agent self-approval attempt (originating agent == QA agent) is rejected by a hard assertion in `qa_gate.py`.

### M3.9 — Run summary generator

**Deliverables**
- `agent_platform/telemetry/run_summary.py` — generates the OKF `summary.md` per masterplan §16.3, with `generated_by`/`evidenced_by` relations back to the SPOC and forward to `events.jsonl`, including every test result produced during the run.

**Definition of done**
- `summary.md` for the M3.8 fixture links to both test results and to the SPOC, and passes the OKF schema and cross-reference validator from Phase 1.

**Phase 3 exit criteria (masterplan):** one bounded SPOC executes end-to-end locally; a run can resume after intentional interruption. ✅ when M3.1–M3.9 are done, using the first vertical slice scenario from masterplan §27 as the end-to-end acceptance test.

---

## 9. Phase 4 — Secure repository and Git tools

**Masterplan reference:** §21 Phase 4, §14.4, §14.5, §22 Epic D (partial)

### M4.1 — Path security kernel

**Deliverables**
- `agent-repository/tools/file_tools/path_guard.py` — canonicalizes paths, rejects paths outside mounted roots, rejects symlink escapes, separates read/write permission checks per manifest allowlist (masterplan §14.4).

**Definition of done**
- Test corpus includes: `../../etc/passwd` traversal, a symlink created inside the allowed root pointing outside it, and a write attempt to a path only granted read access — all rejected with specific error codes.

### M4.2 — Scoped read/write tools

**Deliverables**
- `agent-repository/tools/file_tools/repository_read.py`, `repository_write_scoped.py` — implement atomic writes, file locks, before/after hashing, secret scanning on staged content, and per-call audit events (masterplan §14.4).

**Definition of done**
- A write is rejected if secret-scanning flags the content; the rejection itself is a logged security event (masterplan §16.2).
- Concurrent writes to the same file from two simulated workers are serialized by the file lock without data loss.

### M4.3 — Git branch-per-run tooling

**Deliverables**
- `agent-repository/tools/git_tools/run_branch.py` — creates `run/<spoc-id>/<run-id>`, commits with SPOC ID + run ID in the message, never pushes to protected branches directly (masterplan §14.5).
- `agent-repository/tools/git_tools/pull_request.py` — opens a PR with validation evidence and approval status attached.

**Definition of done**
- An attempted push to `main` from the execution worker identity is rejected by repository branch protection (verifies M0.4 configuration is actually enforced, not just documented).
- A generated PR body includes links to the run summary, test results, and human approval record (if any).

### M4.4 — Checksum manifests and provenance stamping

**Deliverables**
- `agent-repository/tools/validation_tools/checksum_manifest.py` — writes `artifacts/checksums/` entries and stamps generated artifacts with `provenance.run_id` (masterplan §9.1 `provenance` block).

**Definition of done**
- Every artifact produced by the M3.8 fixture run has a checksum manifest entry and a `provenance` block referencing its `run_id`.

### M4.5 — File-mutation attributability test suite

**Deliverables**
- `agent-repository/tests/security/test_file_mutations.py` — asserts every file mutation during a full run is attributable to a specific actor/tool/run and reversible (i.e., present on a run branch, not on `main`, until merged).

**Definition of done**
- 100% of files changed by the Phase 3 vertical-slice run are attributable and reside only on the run branch pre-merge.

**Phase 4 exit criteria (masterplan):** no worker can write outside the manifest allowlist; all file mutations are attributable and reversible. ✅ when M4.1–M4.5 are done.

---

## 10. Phase 5 — Policy, approvals, budgets, and model routing

**Masterplan reference:** §21 Phase 5, §15, §16.2 (approval events), §22 Epic D (remainder)

### M5.1 — Policy engine

**Deliverables**
- `agent_platform/control_plane/policy_engine.py` — attribute-based authorization per masterplan §15.3 (actor, project, classification, operation, path, tool, environment, SPOC), invoked before every side effect, not only at run start.

**Definition of done**
- A policy denial mid-run (e.g., classification downgrade attempted) halts the flow at the next tool call boundary, not only at start.
- Policy decisions are logged as `policy_decision` events and stored in the `policy_decisions` DB entity (masterplan §18.1).

### M5.2 — Human approval service and states

**Deliverables**
- `agent_platform/control_plane/approval_service.py` — implements `waiting_for_human` SPOC state, approval request/grant/reject/expiry events (masterplan §16.2), and the mandatory-approval matrix from §15.7.

**Definition of done**
- Every action type listed in masterplan §15.7 (scope/budget/baseline change, access expansion, policy exception, high-risk inferred capability, external communication, production change, legal/regulatory/safety/financial conclusion, knowledge promotion, new agent/tool activation) is wired to require an approval record before proceeding, verified by one test per action type.
- An expired approval request blocks progress rather than defaulting to approved.

### M5.3 — Model router and profiles

**Deliverables**
- `agent_platform/control_plane/model_router.py` — resolves `default_model_profile` / `model_override` against the model catalog (masterplan §11.1, §26), enforcing data-residency and classification constraints (§15.6) as the most restrictive intersection.

**Definition of done**
- A SPOC requesting a model/classification combination that violates residency or classification rules is rejected at compile time (M3.2), not at runtime.

### M5.4 — Budget, token, runtime, and delegation limits

**Deliverables**
- `agent_platform/control_plane/budget_enforcer.py` — enforces `max_runtime_seconds`, `max_delegation_depth`, `max_child_agent_calls`, `max_total_cost_usd` from the SPOC `procedure.constraints` (masterplan §10.2).

**Definition of done**
- Exceeding any single limit stops the run safely (no partial unrecorded side effects) and emits a `budget_threshold_reached` / budget-exceeded event with enough detail to diagnose which limit was hit.

### M5.5 — Governed capability inference wiring

**Deliverables**
- Wire `capability_inference.py` (M2.3) into the compiler/flow so that low-risk inferred capabilities auto-add per policy and high-risk ones create an approval request via M5.2 (masterplan §12.3).

**Definition of done**
- A high-risk inferred capability blocks progress until approved; a low-risk one proceeds automatically and is recorded as `inferred` (not `explicit`) in the run manifest and matching explanation.

**Phase 5 exit criteria (masterplan):** high-risk operations cannot proceed without authenticated approval; budget exhaustion stops safely. ✅ when M5.1–M5.5 are done.

---

## 11. Phase 6 — API, worker isolation, and shared deployment

**Masterplan reference:** §21 Phase 6, §17, §18

### M6.1 — FastAPI control-plane service

**Deliverables**
- `agent_platform/api/app.py` implementing the REST surface from masterplan §17.2 (projects, SPOC validate/compile/runs, run status/cancel/resume/events, approvals, registry agents/capabilities). Graph and chat endpoints are stubbed here and completed in Phase 9/W9 once the graph generator (section 14) lands.
- OpenAPI spec generated and committed (masterplan §17.3).

**Definition of done**
- OAuth/OIDC auth wired (even if pointed at a dev identity provider), idempotency keys enforced on mutating endpoints, optimistic concurrency on state-changing calls, pagination on list endpoints, correlation IDs propagated end-to-end into the event stream.

### M6.2 — PostgreSQL operational state

**Deliverables**
- `agent_platform/repositories/postgres/` — SQLAlchemy (or equivalent) models for every entity in masterplan §18.1 (projects, spocs, compiled_manifests, runs, run_steps, events, leases, approvals, artifacts, model_usage, tool_calls, policy_decisions, registry_snapshots).
- Migration scripts building on the M1.7 skeleton.

**Definition of done**
- The same test suite from Phase 3 (SQLite-backed) passes unchanged against the PostgreSQL-backed store, proving the storage adapter is swappable (execution principle: interfaces around persistence, mirroring principle 2 for CrewAI).

### M6.3 — Queue-backed workers and lease recovery

**Deliverables**
- `agent_platform/execution_plane/worker.py` — pulls compiled manifests from a queue, acquires a time-limited lease with heartbeat renewal, and executes the Flow (masterplan §18.3).
- Reconciliation logic for expired leases: check for prior side effects before resuming (masterplan §18.3, §19.3).

**Definition of done**
- Simulated worker crash mid-run: a second worker recovers the expired lease, detects any prior side effects, and either resumes safely or reconciles without duplicating irreversible actions.

### M6.4 — Container isolation

**Deliverables**
- `agent-repository/Dockerfile` (or per-service Dockerfiles) mounting only manifest-approved paths into the execution worker container; control-plane and execution-plane run as separate containers/processes.

**Definition of done**
- The execution worker container cannot read paths outside its mounted allowlist even if application-level checks are bypassed (defense in depth, verified with a container-level test).

### M6.5 — SSE event stream and RBAC

**Deliverables**
- `GET /api/v1/runs/{run_id}/events` implemented as Server-Sent Events (masterplan §17.2).
- Role-based access control layered on top of OIDC identities (masterplan §21 Phase 6 build list).

**Definition of done**
- Two concurrent projects run without state leakage: an RBAC test confirms a user scoped to project A cannot read project B's run events or artifacts.

**Phase 6 exit criteria (masterplan):** multiple projects can run without state leakage; worker loss and lease recovery pass tests. ✅ when M6.1–M6.5 are done.

---

## 12. Phase 7 — Project-management workflows

**Masterplan reference:** §21 Phase 7, §8, §22 Epic F

### M7.1 — Project intake and planning/baseline flows

**Deliverables**
- `project-template-repository/workflows/project_intake.yaml` and a corresponding CrewAI flow module producing the G0/G1 artifacts (charter, initial constraints, decision rights) per masterplan §8.2.
- Planning/baseline flow producing the G2 artifacts (WBS, milestones, dependencies, risks, architecture constraints, acceptance strategy), including epic and initial user-story scaffolding (masterplan §8.3, §9.7).

**Definition of done**
- Running the intake + planning flows against a fixture project produces valid G0–G2 stage-gate artifacts that pass the Phase 1 validators, including at least one epic with linked, tested user stories.

### M7.2 — Requirement-to-delivery flow (production hardening)

**Deliverables**
- Promote the Phase 3 vertical-slice flow (`requirement_to_delivery@1.2.0`, masterplan §10.2) to a fully governed workflow entry in `project-template-repository/workflows/`, including the QA rework loop (M3.8) and G3/G4 gate evidence generation.

**Definition of done**
- A reference project can move a user story from `draft` through `accepted`/`closed`, including at least one QA rejection and rework cycle, entirely through this workflow.

### M7.3 — Change-control and risk-escalation flows

**Deliverables**
- `project-template-repository/workflows/change_request.yaml`, `risk_escalation.yaml` and corresponding flow modules, wired to the human approval matrix (masterplan §15.7) for scope/budget/baseline changes.

**Definition of done**
- A simulated scope change cannot alter a baselined plan artifact without an approval record; a critical risk automatically raises a human escalation event.

### M7.4 — RAID and decision-log management

**Deliverables**
- Tooling to create/update `public/risks/`, `public/issues/`, `public/dependencies/`, `public/decisions/` OKF files with correct relations (`depends_on`, `blocks`, `related_to`, etc.) and to keep their indexes current (M1.6 generator reused).

**Definition of done**
- A dependency marked `blocks` on an in-progress SPOC prevents that SPOC from being matched/executed until the blocking item is resolved (or requires explicit override with approval).

### M7.5 — Evidence-grounded status reporting

**Deliverables**
- `agent_platform/execution_plane/status_report_generator.py` — produces `public/status/status_report_<date>.md` (an OKF `status_report`) whose every claim traces to a specific artifact via `reports_on`/`evidenced_by` relations (masterplan §16.3, §9.3).

**Definition of done**
- A status report generated from the fixture project has zero unsourced claims (every sentence describing project state links to an artifact ID); this is enforced by an automated check, not just manual review.

### M7.6 — Project closure and learning flow

**Deliverables**
- `project-template-repository/workflows/project_closure.yaml` producing the G5 closure artifact (handover, unresolved items, operational ownership, lessons learned) and the curated-promotion workflow referenced in masterplan §15.7 (private → global knowledge requires human approval).

**Definition of done**
- Closure flow blocks completion until unresolved risks/issues have owners (masterplan §23 DoD item) and any lesson proposed for promotion to global knowledge has an explicit human approval record.

**Phase 7 exit criteria (masterplan):** a reference project can progress through all stage gates; status reports trace every claim to project evidence. ✅ when M7.1–M7.6 are done.

---

## 13. Phase 8 — Observability, evaluation, and production hardening

**Masterplan reference:** §21 Phase 8, §16.4, §20

### M8.1 — Metrics, traces, dashboards, alerts

**Deliverables**
- OpenTelemetry instrumentation across control plane and execution plane (masterplan §26).
- Dashboards covering the metric families in §16.4: reliability, quality, operations, economics, governance, project value.
- Alert rules for budget exhaustion, dead-letter rate spikes, approval-lead-time SLA breaches, and policy-denial spikes.

**Definition of done**
- Each metric family in §16.4 has at least one dashboard panel and, where safety-relevant (budget, dead-letter, policy denial), at least one alert.

### M8.2 — Regression evaluation suites

**Deliverables**
- `agent-repository/tests/evaluation/<capability>/` datasets per masterplan §20.3 for every capability claimed by an active registry agent, including `qa.acceptance_validation` and `qa.traceability_check`.

**Definition of done**
- CI runs the full evaluation regression suite on every registry change and blocks activation of an agent/capability below its declared `minimum_pass_rate`.

### M8.3 — Failure injection

**Deliverables**
- `agent-repository/tests/security/` and `tests/integration/` failure-injection harness covering the required scenarios from masterplan §20.2 not already covered by earlier phases (tool timeout/retry, duplicate execution, worker loss, Git merge conflict, prompt injection corpus).

**Definition of done**
- Every scenario in masterplan §20.2 has an automated test, and the full list passes in CI.

### M8.4 — Backup, restore, retention, incident runbooks

**Deliverables**
- `agent-repository/docs/operations/backup_restore.md`, `retention_policy.md` (aligned with M0.1 retention decisions), `incident_runbook.md`.
- A disaster-recovery rehearsal script and recorded rehearsal result.

**Definition of done**
- A restore rehearsal from backup succeeds and is documented with timing and data-loss window (no invented numbers; measured from the actual rehearsal).

### M8.5 — Performance and cost optimization pass

**Deliverables**
- Profiling report identifying the top cost/latency contributors (model calls, tool calls, DB queries) and a prioritized optimization backlog.

**Definition of done**
- At least the top identified bottleneck has a committed fix or an explicit, owned deferral decision.

**Phase 8 exit criteria (masterplan):** agreed reliability and quality thresholds are met; security review and operational readiness review approved. ✅ when M8.1–M8.5 are done and both reviews are formally signed off (link to approval records from M5.2).

---

## 14. Phase 9 — Web interface (including knowledge graph and Project Manager chat)

**Masterplan reference:** §21 Phase 9, §9.6, §9.7, §11.4, §13.6, §17.2, §22 Epic G

Because the graph generator and QA/requirements model are needed by the UI but are logically independent of it, split this phase into a backend track (can start once Phase 1 lands, per section 4) and a frontend track (needs Phase 6 API).

### M9.1 — Graph generator (backend track, can start after Phase 1)

**Deliverables**
- `agent_platform/knowledge_graph/graph_generator.py` — walks all OKF files, builds nodes/edges from `id`, `type`, `status`, `owner`, `relations`, `source_refs`, `cross_references`; includes non-OKF leaf nodes (`events.jsonl`, binaries) reachable via `generated_by`/`evidenced_by` (masterplan §9.6).
- Output: `public/knowledge/graph_index.json`, regenerated by `mas graph rebuild` and by CI.
- `agent_platform/knowledge_graph/style_config.yaml` — the type→color/icon table from masterplan §9.6, extended with `epic`, `test_case`, `test_result` styles, as configuration (not hard-coded).

**Definition of done**
- Graph has zero dangling relations on the Phase 7 reference project.
- Regenerating the graph twice on an unchanged tree is idempotent (same rule as M1.6).
- Every node's `type` resolves to a style entry; an unknown `type` fails CI rather than rendering unstyled.

### M9.2 — Graph and chat REST endpoints

**Deliverables**
- Implement the stubbed endpoints from M6.1: `GET /api/v1/graph`, `GET /api/v1/graph/nodes/{node_id}`, `GET /api/v1/graph/nodes/{node_id}/neighbors`, `POST /api/v1/chat/sessions`, `POST /api/v1/chat/sessions/{session_id}/messages`, `GET /api/v1/chat/sessions/{session_id}/stream`.

**Definition of done**
- Graph endpoints serve directly from `graph_index.json` (no re-parsing OKF files per request).
- Chat endpoints authorize scope per M5.1 policy engine before answering (classification-aware, masterplan §11.4).

### M9.3 — Project Manager agent and query flow

**Deliverables**
- `agent_platform/execution_plane/pm_query_flow.py` implementing the flow in masterplan §13.6: `load_session_state → authorize_query_scope → query_graph_and_evidence → compose_grounded_answer → attach_citations → log_chat_event → end`.
- Registry entry for `project_manager_agent` (masterplan §11.4) with read-only tools only: `graph_query_tool`, `artifact_search_tool`, `status_aggregator_tool`, `run_evidence_reader_tool`. No write/Git/delegation tools.
- `mas chat` CLI command.

**Definition of done**
- The agent cites the OKF `id` of every artifact it uses in a substantive answer; a test asserts responses without sufficient grounding explicitly say so rather than fabricating.
- The agent cannot access `confidential`/`restricted` artifacts unless explicitly permitted by classification rules (masterplan §15.6), verified by a negative test.
- Chat sessions are logged as run-style events (masterplan §11.4) and never mutate project state (verified: a chat session cannot alter SPOC state, files, or approvals).

### M9.4 — Web UI: project overview, SPOC editor, run/approval views

**Deliverables**
- Frontend app (framework choice recorded as an ADR extension of M0.2) implementing: project overview, SPOC editor with live schema validation against `spoc.schema.json`, run timeline + evidence viewer, approval inbox, agent/capability registry views, cost/quality dashboards (masterplan §21 Phase 9 build list).

**Definition of done**
- SPOC editor rejects an invalid SPOC client-side using the same schema as the backend (single source of truth, no schema drift).

### M9.5 — Web UI: knowledge graph view and document viewer

**Deliverables**
- Interactive graph view rendering `graph_index.json` with the M9.1 style config and a visible legend.
- Document viewer rendering an OKF file plus its relations/source_refs/cross_references as clickable links, including backlinks.
- Deep links resolved by stable OKF `id`, not file path.
- "Jump to evidence" action from any outcome/deliverable/decision node to its run summary and then to `events.jsonl`.
- Search/filter by type, tag, status, owner, classification.

**Definition of done**
- A user can navigate, using only UI clicks, from a project outcome → its SPOC → its run summary → its raw log evidence (masterplan §21 Phase 9 exit criterion), verified with an end-to-end UI test.

### M9.6 — Web UI: persistent Project Manager chat panel

**Deliverables**
- Chat panel component mounted globally (available from every screen), backed by M9.2/M9.3, rendering citations as clickable links into the graph/document viewer.

**Definition of done**
- The chat panel is present and functional on every top-level screen; every answer's citations resolve to a valid, existing graph node (no dead citation links).

### M9.7 — Regression tests for graph and QA traceability integrity

**Deliverables**
- `tests/integration/test_graph_integrity.py` — asserts every generated `summary.md` links back to its SPOC and forward to its raw events; asserts the graph has no orphaned/dangling relations; asserts every requirement's coverage/pass status matches its linked test results (masterplan §22 Epic G, Epic H).

**Definition of done**
- Suite passes against the full reference project built across Phases 1–7.

**Phase 9 exit criteria (masterplan):** UI is a client of the same API and does not bypass policy; a user can navigate from any outcome to SPOC, run summary, and raw log evidence using only graph/document-viewer links; the PM chat panel is reachable from every screen with citations linking back to graph nodes. ✅ when M9.1–M9.7 are done.

---

## 15. Cross-cutting checklist applied at every phase boundary

Before declaring any phase "done," confirm:

- [ ] All schemas touched in the phase have valid + invalid fixtures and pass CI (masterplan §20.1 item 1).
- [ ] All new tools have contract tests (masterplan §20.1 item 2, §14.1).
- [ ] All new repository adapters have integration tests against both SQLite and (once available) PostgreSQL (masterplan §20.1 item 3).
- [ ] All new flow steps have transition tests (masterplan §20.1 item 4).
- [ ] All new authorization-sensitive code paths have security/authorization tests (masterplan §20.1 item 5).
- [ ] All new agent capabilities have golden-scenario evaluations (masterplan §20.1 item 6).
- [ ] Failure-injection tests exist for any new failure mode introduced (masterplan §20.1 item 7).
- [ ] The phase's masterplan "Exit criteria" bullets are individually verified, not just implied by passing unit tests.
- [ ] The per-SPOC Definition of Done (masterplan §23) still holds for at least one live example produced during the phase.
- [ ] No new artifact type was introduced without: schema, template, linter rule, and (if applicable) graph style entry (section 9.1 above ties this to Phase 1/9 specifically, but it applies to any phase that adds a `type`).

---

## 16. Suggested first three milestones to execute immediately

For a coding agent picking this plan up cold, the recommended entry point is:

1. **M0.1 and M0.2** — without resolved inception decisions and recorded ADRs, later schema and policy choices (data classification × model provider, approval matrix specifics) are guesses, not decisions.
2. **M1.1–M1.6** — the repository skeletons and OKF/SPOC schemas are the foundation every other milestone depends on; nothing in Phase 2+ should begin before the OKF linter and cross-reference validator exist and are enforced in CI.
3. **M2.1–M2.3** — the deterministic matcher is required before any real CrewAI flow (Phase 3) can select an agent for a task; it should be built and unit-tested against fixtures before wiring it into the flow.

From there, follow the phase order in section 4, using the vertical slice in masterplan §27 as the running end-to-end acceptance test from Phase 3 onward.
---

---

## 17. Documentation-as-code strategy

### 17.1 Binding objective

The complete project shall be documented in version-controlled Markdown. The documentation structure shall mirror the implemented project structure so that a reviewer can navigate bidirectionally between project goal, requirement, workflow, code unit, test case, test result, defect, and release decision.

Documentation is part of the implementation. A change is not complete when code, behavior, schemas, configuration, or tests change without the corresponding Markdown documentation in the same pull request.

### 17.2 Documentation principles

1. **One source of truth per fact.** Code is authoritative for executable behavior, schemas for machine validation, and Markdown for intent, contracts, decisions, usage, limitations, and evidence.
2. **Mirror without copying.** Documentation follows source structure but does not reproduce implementations line by line.
3. **Stable IDs.** Every documentable code unit, test case, test run, requirement, workflow, tool, agent, and decision receives a stable ID.
4. **Atomic change.** Code, documentation, tests, and traceability are delivered together.
5. **Machine-checkable completeness.** CI detects missing or orphaned documentation, stale generated sections, broken links, and undocumented tests.
6. **Markdown remains authoritative.** A static documentation site may be generated, but the `.md` files remain the durable source.
7. **Generated content is marked and reproducible.** Generated indexes, signatures, API references, and result summaries must not be edited manually.
8. **No secrets or hidden reasoning.** Documentation and test evidence contain only approved, redacted engineering information.

### 17.3 What requires a corresponding Markdown file

A dedicated Markdown file is mandatory for every documentable code unit:

- Public class, protocol/interface, and domain-significant enum
- CrewAI Flow class, Crew factory, and Task factory
- Application service and use-case handler
- Port/interface and infrastructure adapter
- Registered tool, agent adapter, and model adapter
- Repository, policy, approval, and persistence implementation
- API resource/controller group and CLI command group
- Worker, scheduled job, schema, and migration
- Security-critical internal class, even when private

Trivial private helpers and simple value objects may be documented in the owning `module.md`. Any helper with security, persistence, policy, orchestration, concurrency, or non-obvious domain behavior requires its own document.

### 17.4 Mirrored folder structure

```text
agent-repository/
├── src/agent_platform/
│   ├── domain/project.py
│   ├── domain/run.py
│   ├── application/compile_spoc.py
│   ├── application/ports/run_state_store.py
│   └── execution_plane/flows/project_execution_flow.py
└── docs/
    ├── index.md
    ├── architecture/
    ├── decisions/
    ├── implementation/agent_platform/
    │   ├── domain/project/
    │   │   ├── module.md
    │   │   ├── Project.md
    │   │   └── ProjectStatus.md
    │   ├── domain/run/
    │   │   ├── module.md
    │   │   ├── Run.md
    │   │   └── RunAttempt.md
    │   ├── application/compile_spoc/
    │   │   ├── module.md
    │   │   └── CompileSpocService.md
    │   ├── application/ports/run_state_store/
    │   │   ├── module.md
    │   │   └── RunStateStore.md
    │   └── execution_plane/flows/project_execution_flow/
    │       ├── module.md
    │       └── ProjectExecutionFlow.md
    ├── api/
    ├── cli/
    ├── configuration/
    ├── security/
    ├── operations/
    ├── testing/
    └── generated/
```

A Python module maps to a documentation directory named after the module. `module.md` documents the whole module. Each documentable class receives `<ClassName>.md`. This handles modules containing multiple classes without ambiguity.

Equivalent Markdown documentation roots are required in the project-template repository for schemas, templates, workflows, and governance, and in each active-project repository for project-specific configuration, workflows, operating instructions, and implementation extensions. Governed project facts and deliverables remain under `public/` and `private/`; `docs/` explains implementation and operation rather than replacing project knowledge.

### 17.5 Code-document front matter

```yaml
---
schema_version: code-doc/1.0
doc_id: CODE-DOC-COMPILE-SPOC-001-EXAMPLE
code_unit_id: CODE-COMPILE-SPOC-SERVICE
title: CompileSpocService
code_ref: src/agent_platform/application/compile_spoc.py#CompileSpocService
unit_type: application_service
status: active
owner_role: platform_engineering
introduced_in: M3.2
classification: internal
related_requirements: [REQ-PLAT-001]
related_adrs: [ADR-003]
related_test_cases: [TC-COMPILER-001]
last_verified_commit: "<generated-by-ci>"
---
```

`last_verified_commit` is generated after successful verification. It is never guessed or manually asserted.

### 17.6 Mandatory class-document contents

Each class document contains:

- Purpose
- Classification of the code unit
- Responsibilities
- Explicit non-responsibilities
- Public contract, inputs, outputs, methods, typed errors, and side effects
- Invariants
- State and lifecycle
- Concurrency and transaction assumptions
- Dependencies and dependency direction
- Security and data-classification behavior
- Failure, timeout, retry, cancellation, idempotency, and recovery behavior
- Events, metrics, traces, and correlation identifiers
- Minimal usage or sequence example
- Linked requirements, ADRs, workflows, and schemas
- Linked test cases and latest accepted evidence
- Material change history

### 17.7 Documentation categories

The project must maintain:

- `docs/index.md`: generated navigation and documentation-coverage report
- `docs/architecture/`: context, container, component, sequence, state, trust-boundary, and deployment views
- `docs/decisions/`: ADRs and inception decisions
- `docs/implementation/`: mirrored module and class documentation
- `docs/api/`: endpoint behavior, authorization, errors, and examples
- `docs/cli/`: commands, parameters, outputs, and exit codes
- `docs/configuration/`: configuration keys, defaults, classification, and environment behavior
- `docs/security/`: threat model, controls, abuse cases, and security-test links
- `docs/operations/`: deployment, migration, backup, restore, reconciliation, incident, and recovery runbooks
- `docs/testing/`: strategy, plans, cases, runs, evidence, defects, traceability, and release reports
- `docs/generated/`: reproducible projections only
- `docs/glossary.md`: controlled platform vocabulary

### 17.8 Documentation tooling and CI

Implement:

```text
mas docs scaffold --code-ref <path#symbol>
mas docs validate
mas docs coverage
mas docs build
mas docs serve
mas docs link-check
mas docs changed
```

`mas docs validate` shall use Python AST analysis rather than importing application code. It verifies:

- Code-unit discovery and code-to-document mapping
- Document-to-code reverse mapping
- Front-matter schema and stable-ID uniqueness
- Required sections
- Valid links and anchors
- Requirement, ADR, workflow, and test relationships
- Orphaned documents for removed code
- Missing documents for required code units
- Generated-section checksums
- Mermaid/build validity where supported
- Documentation of security-critical private classes

Documentation coverage is:

```text
documented_required_code_units / discovered_required_code_units
```

A code unit counts only when its document exists, validates, resolves to the code symbol, contains all required sections, and links to relevant tests or an approved test exemption. Protected release branches require 100 percent coverage for required code units.

### 17.9 Lifecycle and review

Documentation states are `draft`, `active`, `deprecated`, and `retired`. Active code cannot have draft documentation. Refactoring a path preserves the stable documentation ID and updates `code_ref`. Semantic replacement creates a new ID with a `supersedes` relation. CODEOWNERS applies jointly to source and documentation. Security-sensitive documentation requires security review, and architecture changes require ADR linkage.

---

## 18. Test strategy and test-documentation model

### 18.1 Required outcomes

The documentation must answer for every test:

- What was tested and why?
- Which requirement, risk, workflow, class, contract, or defect was verified?
- How was it tested?
- Which data, fixtures, environment, model, prompt, tool, and version were used?
- What result was expected?
- What result occurred?
- Was it passed, failed, blocked, skipped, or inconclusive?
- Where is the immutable evidence?
- What defect or follow-up resulted?
- Which release decision relied on it?

### 18.2 Mirrored test documentation structure

```text
agent-repository/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── architecture/
│   ├── integration/
│   ├── security/
│   ├── evaluation/
│   ├── resilience/
│   ├── performance/
│   ├── end_to_end/
│   └── fixtures/
└── docs/testing/
    ├── strategy/
    │   ├── test_strategy.md
    │   ├── test_documentation_standard.md
    │   ├── environments.md
    │   ├── data_management.md
    │   ├── model_evaluation_policy.md
    │   └── release_quality_gates.md
    ├── plans/<release-or-milestone>/test_plan.md
    ├── cases/
    │   ├── unit/
    │   ├── contract/
    │   ├── architecture/
    │   ├── integration/
    │   ├── security/
    │   ├── evaluation/
    │   ├── resilience/
    │   ├── performance/
    │   └── end_to_end/
    ├── runs/<test-run-id>/
    │   ├── summary.md
    │   ├── environment.md
    │   ├── results/<test-case-id>.md
    │   └── evidence_manifest.md
    ├── defects/
    ├── traceability/
    │   ├── requirements_to_tests.md
    │   ├── code_to_tests.md
    │   ├── risks_to_tests.md
    │   └── workflows_to_tests.md
    └── reports/<release>/test_summary_report.md
```

### 18.3 One Markdown document per logical test case

Every logical test case receives a stable test ID and one Markdown file. Parameterized executions may share one test-case document only when they verify the same behavior. Materially different expected behavior receives a separate test ID.

Example front matter:

```yaml
---
schema_version: test-case/1.1
test_case_id: TC-RUNSTATE-RESUME-001-EXAMPLE
title: Resume a suspended run from the authoritative checkpoint
test_type: integration
status: active
risk_level: high
owner_role: runtime_engineering
automation:
  framework: pytest
  code_ref: tests/integration/runtime/test_resume.py#test_resume_from_checkpoint
system_under_test:
  - CODE-RUN-STATE-STORE
  - CODE-PROJECT-EXECUTION-FLOW
verifies_requirements: [REQ-RUN-014]
mitigates_risks: [RISK-RUNTIME-003]
related_adrs: [ADR-011, ADR-012]
fixtures: [FIX-RUN-VALID-001]
classification: internal
---
```

Required body sections:

- Purpose and scope
- Preconditions
- Test data and fixtures
- Environment requirements
- Logical procedure
- Expected results
- Pass criteria
- Failure interpretation
- Evidence to capture
- Automation mapping
- Traceability
- Review history

Automated-test procedure describes the logical method, not every line of test code. Manual tests require reproducible steps.

### 18.4 Automated test mapping

Automated tests carry a test-case marker:

```python
@pytest.mark.test_case("TC-RUNSTATE-RESUME-001")
def test_resume_from_checkpoint(...):
    ...
```

CI verifies that every collected test has a test-case ID or belongs to an explicitly documented generated/property-based test family, and that every active test-case document maps to executable test code or is explicitly manual. Duplicate, missing, and orphaned mappings fail validation.

### 18.5 Test-result documents

Every execution creates a generated, immutable Markdown result. A rerun creates a new result and does not overwrite the previous one.

```yaml
---
schema_version: test-result/1.1
test_result_id: TR-EXAMPLE-TC-RUNSTATE-RESUME-001
test_run_id: TEST-RUN-001
test_case_id: TC-RUNSTATE-RESUME-001
outcome: passed
started_at: "<utc-timestamp>"
finished_at: "<utc-timestamp>"
executor_type: deterministic_tool
executor_ref: test.pytest@1.0.0
code_commit: "<git-commit>"
manifest_hash: "sha256:..."
environment_ref: ../environment.md
evidence_refs: [evidence/junit.xml, evidence/log.txt]
classification: internal
integrity_hash: "sha256:..."
---
```

Each result explains objective, configuration, execution method, expected result, actual result, outcome and reason, evidence, deviations, defects, and reviewer conclusion. Failed, blocked, skipped, and inconclusive outcomes require an explicit reason.

### 18.6 Test-run summary

Each run summary includes scope, trigger, code commit, environment, container digest, dependency-lock hash, schema/workflow/policy versions, selected model and prompt hashes where relevant, included and excluded suites, outcomes from runner data, linked failures and defects, traceability coverage, flaky/quarantine status, approved deviations, release-gate conclusion, and evidence-manifest hash.

### 18.7 Test layers

- **Unit:** pure domain behavior, parsing, validation, matching, and routing. No network or real models.
- **Contract:** each port, adapter, and tool against schemas, authorization, errors, idempotency, timeout, cancellation, and redaction contracts.
- **Architecture:** dependency direction, forbidden imports, package boundaries, registry mappings, and code-document completeness.
- **Integration:** real component combinations such as DB transaction plus outbox, Git, object store, policy, checkpoint, and resume.
- **Security:** path traversal, symlink escape, prompt injection, cross-project access, classification breaches, secret leakage, SSRF, malicious files, privilege escalation, stale approvals, and unsafe fallback.
- **Agent evaluation:** versioned datasets and rubrics with model, prompt, tools, knowledge snapshot, repeated-run policy, scoring, and prohibited behavior. One model output is not deterministic proof.
- **Resilience:** worker loss, timeout, provider failure, duplicate or out-of-order events, DB restart, stale leases, event-projection failure, cancellation, and partial side effects.
- **Performance and cost:** latency, throughput, memory, storage, tokens, cost, graph size, and workload profile.
- **End-to-end:** project goal and SPOC through execution, validation, approval, evidence, Git integration, and closure.
- **Manual/exploratory:** usability, accessibility, operational rehearsal, and non-deterministic scenarios, still with documented procedure and evidence.

### 18.8 Test data and environments

Synthetic data is the default. Production data is prohibited unless an approved sanitized-data process exists. Every fixture has an ID, owner, classification, source, generation method, and retention rule. Golden files are versioned, and changes require a reason. Secrets are injected through test-safe providers. Evaluation data is reviewed for confidentiality, licensing, leakage, and contamination.

Document local deterministic, CI, shared integration, security, performance, and pre-production acceptance environments. Each describes topology, data classifications, model and network access, identity mode, secrets source, reset procedure, observability, and deviations from production.

### 18.9 Traceability

```text
Project goal
 -> Outcome
  -> Requirement / Control / Risk
   -> SPOC / Workflow
    -> Code unit
     -> Test case
      -> Test result
       -> Release decision
```

Typed references in front matter are authoritative. CI generates human-readable matrices. Releases require mandatory requirements to have tests, high and critical risks to have mitigation and verification, documentable code units to have tests or approved exemptions, and acceptance criteria to have evidence tied to the release candidate.

### 18.10 Flaky tests, defects, and exceptions

Flaky status requires evidence, owner, defect, scope, and review date. Quarantine cannot be used merely to make CI green. A passing rerun does not erase a failure. Critical quarantined tests block release without an explicit, scoped, expiring exception.

Every defect document links discovery evidence, affected requirement/code/workflow/release, severity, reproduction, expected and actual behavior, evidence, root-cause status, fix, regression test, and closure evidence. Unconfirmed root cause is identified as such.

### 18.11 Quality gates

Mandatory gates include:

- No unresolved critical security or cross-project isolation failure
- No missing documentation for required code units and release tests
- No orphaned mandatory requirement
- No invalid evidence manifest
- No overwritten test results
- No undocumented test exception or quarantine
- Current generated traceability and documentation indexes
- Deterministic critical failures cannot be silently overridden

Numeric thresholds for coverage, mutation, evaluation, latency, and cost are fixed only after a measured baseline and are defined per test layer or capability.

### 18.12 Pull-request pipeline

A protected-branch pull request runs:

1. Repository structure validation
2. Schema and front-matter validation

---

## 17. Deep-review outcome and binding corrections

### 17.1 Overall assessment

The implementation plan is strong in structure, traceability, security intent, and testability. It is materially more executable than a conventional architecture roadmap. The deep review nevertheless identified several dependency inversions and areas where a coding agent could implement behavior that is internally consistent but operationally wrong.

The most important correction is that Phase 3 currently asks the canonical flow to execute approval, repository mutation, Git, retry, and durable-resume behavior before the production implementations of those capabilities exist in Phases 4 through 6. The revised rule is:

- Phase 3 delivers an end-to-end **local vertical slice through explicit ports and test doubles**.
- Phase 4 replaces repository and Git test doubles with hardened adapters.
- Phase 5 replaces approval, policy, model, and budget test doubles with production control-plane services.
- Phase 6 replaces local scheduling and persistence with shared deployment adapters.
- No Phase 3 implementation may embed provisional security, approval, persistence, or Git behavior inside the CrewAI Flow class.

A second important correction is that CrewAI Flow persistence and the platform's operational state must not become two independent sources of truth. A single `RunStateStore` port owns platform checkpoints. A CrewAI persistence adapter may back that port, or the platform database may back it, but the system must not commit one checkpoint to CrewAI storage and another separately to SQLite/PostgreSQL without an explicit transaction and reconciliation design.

A third correction is that an AI QA agent must not be the executor of deterministic tests. The QA agent can plan, interpret, and review evidence. Actual schema validation, unit tests, security scans, and policy checks run through deterministic tools. Their immutable outputs become evidence consumed by the QA agent. Human acceptance remains separate from both.

### 17.2 Severity-ranked findings

#### Critical findings

1. **Dependency inversion in M3.3.** The canonical flow references approvals, secure writes, Git commits, and pull requests that are only implemented later. Resolve through ports and test doubles, not placeholder logic inside the Flow.
2. **Competing persistence authorities.** M3.6 proposes custom snapshots while CrewAI supports Flow state persistence. Select and document one checkpoint authority behind `RunStateStore`.
3. **Ambiguous attempt identity.** M3.8 says each rework attempt is a new run, while the SPOC flow and event model imply one resumable run. Adopt the identity model in section 19.2 below.
4. **QA-agent overreach.** Deterministic tests must execute in tool runners, not through free-form agent reasoning. The QA agent evaluates evidence and coverage.
5. **Project goal is not implemented explicitly.** The masterplan now expects project goals and outcomes, but Phase 1 lacks a `project.schema.json`, charter templates, and goal-alignment validation.
6. **Small-task execution is not modeled.** The plan needs explicit `atomic`, `delegated`, `crew`, and `workflow` execution modes so a small task does not require a heavyweight Crew.
7. **Workflow definition is underspecified.** Python Flow implementation, workflow catalog entry, and project-template workflow YAML need explicit versioned mapping and compatibility checks.

#### High findings

1. JSONL and database events can diverge without an outbox or reconciliation rule.
2. Branch-per-run can conflict with retry attempts and concurrent SPOCs touching the same artifacts.
3. Registry schema ownership is unclear because schemas live in the template repository while runtime registry code lives in the agent repository.
4. `index.md` generated-file protection cannot reliably infer who edited a file. CI should regenerate and fail on diff.
5. `status_report` sentence-level sourcing is too brittle. Claims need typed claim blocks or claim IDs.
6. The standing Project Manager agent should be a logical project-scoped service, not a permanently resident process or long-lived model context.
7. Model/provider behavior, prompt versions, tool versions, and retrieval configuration need a complete execution fingerprint in the manifest.
8. Three independent repositories need release coordination, compatibility constraints, and integration-test fixtures.
9. The plan lacks a formal package/module dependency rule preventing execution-plane code from importing infrastructure directly.
10. The plan does not define binary artifact storage thresholds, content addressing, malware scanning, or retention enforcement.

#### Medium findings

1. `100% of score weight` in M2.4 should mean mathematically normalized configured factors, including explicitly recorded unavailable factors.
2. The scaffold in M2.5 should be valid with `status: draft`, but activation should fail. Intentionally generating schema-invalid files creates unnecessary friction.
3. `project validate` should support fast and full modes.
4. Schema compatibility and migration policy need explicit backward/forward compatibility rules.
5. Capability relevance based on project context needs a deterministic feature definition or must be disabled in MVP scoring.
6. Unknown graph node types should normally receive a safe fallback style and a CI warning in development; production releases may enforce a hard error.
7. Dates in generated status-report filenames can collide; use stable IDs plus UTC timestamps or reporting-period identifiers.
8. Evaluation datasets and prompts may contain sensitive data and need classification and retention controls.

### 17.3 Binding change map to original milestones

| Original milestone | Required change |
|---|---|
| M0.1 | Add decisions on orchestration backend, checkpoint authority, event authority, queue, object storage, policy engine technology, repository hosting, deployment topology, and build-versus-reuse gates. |
| M0.2 | Add ADR-011 through ADR-022 listed in section 18. |
| M1.2 | Split base OKF schema and type profiles; add project, outcome, milestone, claim, approval, workflow, manifest, and artifact-descriptor profiles. |
| M1.3 | Add `alignment`, `execution_mode`, `attempt_policy`, expected side effects, and workflow compatibility fields to the SPOC schema. |
| M1.5 | Validate IDs through a generated ID index; do not resolve only by mutable file path. Add cycle and illegal-relation validation. |
| M1.6 | CI regenerates projections and fails on Git diff. Do not try to detect the editor identity. |
| M1.8 | Add `--mode fast|full`, `--format text|json|sarif`, and `--changed-only`. |
| M2.3 | Separate team composition from agent scoring. Persist matcher inputs, normalized weights, and tie-break result. |
| M2.5 | Scaffold is schema-valid with `status: draft`; activation validator enforces completeness. |
| M3.2 | Produce a complete execution fingerprint and use a deterministic `execution_key` separate from `run_id`. |
| M3.3 | Depend only on application ports. Use fake approval, repository, Git, event, checkpoint, and tool-execution adapters in Phase 3. |
| M3.6 | Replace `local_store.py` with a `RunStateStore` interface plus SQLite adapter. Decide whether CrewAI persistence is the adapter or an implementation detail. |
| M3.7 | Add an event outbox or explicit dual-write reconciliation between operational DB and JSONL evidence. |
| M3.8 | Deterministic `TestExecutor` tools produce test evidence. QA agent reviews evidence. Adopt run/attempt identity model in section 19.2. |
| M4.2 | Add content-type limits, artifact size limits, malware scanning hook, encoding validation, and quarantine. |
| M4.3 | Branch by work package, not blindly by retry attempt; define conflict and stale-base handling. |
| M5.1 | Use policy decision IDs and policy bundle versions in every authorization event. |
| M5.2 | Add approval object version, subject, scope, expiry semantics, segregation-of-duties, and stale-approval invalidation. |
| M5.3 | Add provider health, fallback policy, feature compatibility, and data-processing policy. Model fallback must never broaden data access. |
| M6.1 | Add API versioning, problem-details schema, request-size limits, upload strategy, and authorization tests per endpoint. |
| M6.2 | Add transactional outbox/inbox tables, unique constraints, artifact versions, and schema migration compatibility tests. |
| M6.3 | Select a concrete worker/queue mechanism through ADR. Do not write a custom broker. |
| M7.1 | Add machine-readable project goal, outcomes, success criteria, scope, assumptions, and traceability rules. |
| M7.5 | Replace sentence-level sourcing with structured claim records rendered into Markdown. |
| M8.1 | Define metric formulas, units, labels, cardinality limits, and ownership before dashboards. |
| M9.3 | Implement PM chat as a stateless service over authorized project-scoped sessions, not a permanently resident agent instance. |

---

## 18. Additional required architecture decisions

The following ADRs are mandatory before relevant implementation begins:

- **ADR-011: Workflow execution substrate.** Decide whether CrewAI Flow persistence alone is sufficient for the first production scope, or whether a durable workflow engine is required. Record the exit criteria that would trigger migration.
- **ADR-012: Checkpoint authority.** Select the authoritative state checkpoint and define how application state, Flow state, and database state map to it.
- **ADR-013: Event authority and evidence projection.** Decide whether the database event ledger or JSONL is authoritative and define atomic publication/reconciliation.
- **ADR-014: Run, attempt, and child-run identity.** Adopt the model in section 19.2.
- **ADR-015: Workflow definition split.** Define the contract between Python Flow code, workflow catalog metadata, and project-template workflow YAML.
- **ADR-016: Policy engine.** Select library/service and policy bundle format. Define fail-closed behavior and local-development behavior.
- **ADR-017: Queue and worker platform.** Select an existing queue/workflow technology. Custom queue implementation is out of scope.
- **ADR-018: Artifact storage.** Set Git size threshold, object-storage mode, content-addressing, malware scanning, and retention.
- **ADR-019: Multi-repository release compatibility.** Define version ranges, compatibility matrix, release train, and integration-test process.
- **ADR-020: Deterministic testing versus agentic QA.** Establish the evidence producer/reviewer separation.
- **ADR-021: Small-task execution modes.** Define atomic, delegated, crew, and workflow semantics.
- **ADR-022: Build-versus-reuse decision.** Record fit-gap outcomes for CrewAI AMP, the internal Agent Factory if accessible, APM concepts, LangGraph/Temporal-style durable orchestration, coding-agent backends, and existing PM systems. No adoption is implied; each is evaluated against requirements.

### 18.1 ADR acceptance format

Every ADR must contain:

- Decision owner
- Decision date
- Status
- Scope
- Options considered
- Decision drivers
- Selected option
- Rejected options and reason
- Security and compliance impact
- Operational impact
- Cost impact category
- Portability impact
- Revisit trigger
- Supersedes/superseded-by links
- Related milestones and tests

---

## 19. Corrected domain and execution model

### 19.1 Project goal and alignment

Add `project.schema.json` and project-charter templates in Phase 1. The minimum project control document is:

```yaml
schema_version: project/1.0
project_id: PRJ-001
name: Example Project
status: planning
classification: internal
goal:
  statement: "Deliver the agreed target outcome."
  target_state: "A measurable description of the desired end state."
  business_value: "Why the project exists."
outcomes:
  - id: OUT-001
    statement: "A measurable result."
    success_measure_ref: SC-001
success_criteria:
  - id: SC-001
    metric: acceptance_rate
    operator: gte
    target: 0.95
scope:
  in_scope: []
  out_of_scope: []
assumptions: []
constraints: []
charter_ref: public/charter/project_charter.md
```

Every epic, requirement, user story, change request, milestone, deliverable, and SPOC must trace to at least one outcome, control obligation, risk response, or approved operational-maintenance purpose. The validator emits a hard error for accepted work without alignment and a warning for draft work.

Add this SPOC block:

```yaml
alignment:
  project_goal_ref: project.yaml#goal
  outcome_refs: [OUT-001]
  requirement_refs: [REQ-001]
  milestone_refs: [MS-001]
  contribution_statement: "Explains how this work contributes."
```

### 19.2 Run and attempt identity

Use these identities consistently:

- `spoc_id`: stable governed work-package identity.
- `spoc_version`: immutable content hash or version.
- `execution_key`: deterministic hash of project, SPOC version, resolved inputs, workflow version, policy bundle, and caller-provided idempotency scope.
- `run_id`: one logical execution lifecycle for an execution key.
- `attempt_id`: one processing attempt within a run, including QA rework.
- `step_id`: one Flow step execution.
- `tool_call_id`: one tool invocation.
- `child_run_id`: separately governed delegated execution linked to its parent.

A QA rework normally creates a new `attempt_id` under the same `run_id`. A new `run_id` is created only when the SPOC version, material input versions, workflow version, approval scope, or explicit operator intent changes. This preserves one auditable lifecycle while distinguishing retries from changed work.

### 19.3 Execution modes

Add an enum to the SPOC:

```yaml
procedure:
  execution_mode: atomic
```

Modes:

- `atomic`: one agent or direct deterministic tool pipeline inside the minimal control Flow.
- `delegated`: one primary agent may invoke bounded specialist child runs.
- `crew`: a bounded Crew coordinates multiple specialists.
- `workflow`: the Flow coordinates multiple work packages or Crews through project stages.

All modes use the same control envelope: compile, authorize, budget, execute, validate, evidence, and finalize. `atomic` must not instantiate a Crew when a direct task or deterministic tool is sufficient.

### 19.4 Workflow definition contract

Use three artifacts:

1. Python implementation in `agent_platform/execution_plane/flows/<flow>.py`.
2. Registry entry in `agent-repository/registry/workflows/<workflow-id>/<version>.yaml`.
3. Project-method template in `project-template-repository/workflows/<workflow-id>/<version>.yaml`.

The registry entry binds implementation and template:

```yaml
workflow_id: requirement_to_delivery
version: 1.2.0
implementation:
  module: agent_platform.execution_plane.flows.requirement_to_delivery
  class: RequirementToDeliveryFlow
state_schema: project-run-state/1.0
template_contract: requirement-to-delivery/1.2
supported_execution_modes: [atomic, delegated, crew, workflow]
compatible_platform: ">=1.0.0,<2.0.0"
status: active
```

Compiler checks must prove that all three versions are compatible before a manifest is issued.

### 19.5 State ownership

State categories and authorities:

| State | Authority | Projection |
|---|---|---|
| Project facts and approved artifacts | Git/OKF | Graph/index/search |
| Current run state | RunStateStore | API/SSE/read models |
| Immutable execution events | Event ledger | JSONL run evidence |
| Large binary content | Object store | Git artifact descriptor |
| Secrets | Secrets manager | Never projected into prompts/logs |
| Agent conversational context | Session store with retention | Not project truth |

The Flow state contains references and status needed for orchestration. It does not become the project knowledge store.

---

## 20. Application architecture and dependency rules

### 20.1 Required ports

Define these protocols/interfaces before M3.3:

```text
RunStateStore
EventLedger
ArtifactRepository
GitWorkspace
PolicyDecisionPoint
ApprovalGateway
ModelGateway
ToolExecutor
AgentRuntime
WorkflowRegistry
IdentityContext
BudgetMeter
Clock
IdGenerator
SecretsProvider
ObjectStore
```

Phase 3 uses in-memory or local safe adapters. Later phases replace them through dependency injection.

### 20.2 Dependency direction

```text
domain
  <- application services
      <- control-plane / execution-plane adapters
          <- infrastructure adapters
```

Rules:

- `domain/` imports no CrewAI, FastAPI, SQLAlchemy, Git, cloud SDK, or model-provider package.
- Flow classes call application services through ports.
- Tools never query the database directly unless their contract explicitly identifies them as infrastructure adapters.
- API handlers contain no business decisions.
- Pydantic transport models are mapped to domain models at boundaries.
- Infrastructure exceptions are translated to typed platform errors before reaching Flow routing.

Add an import-boundary test, for example using a dependency-rule test package or a custom AST check.

### 20.3 Suggested package layout

```text
src/agent_platform/
├── domain/
│   ├── project.py
│   ├── spoc.py
│   ├── run.py
│   ├── workflow.py
│   ├── capability.py
│   ├── approval.py
│   └── events.py
├── application/
│   ├── ports/
│   ├── compile_spoc.py
│   ├── start_run.py
│   ├── execute_step.py
│   ├── validate_output.py
│   └── finalize_run.py
├── adapters/
│   ├── crewai/
│   ├── persistence/
│   ├── git/
│   ├── policy/
│   ├── models/
│   └── tools/
├── control_plane/
├── execution_plane/
│   └── flows/
├── api/
├── cli/
└── telemetry/
```

### 20.4 Execution fingerprint

Every manifest records:

- Platform version and Git commit
- CrewAI version
- Flow implementation module/class and code hash
- Workflow/template versions and hashes
- SPOC version/hash
- Input artifact hashes
- Agent definitions and prompt hashes
- Capability catalog version
- Skill and tool versions
- Model provider, model identifier, and resolved profile
- Model parameters relevant to reproducibility
- Retrieval configuration and knowledge snapshot identifiers
- Policy bundle version/hash
- Approval policy version
- Schema versions
- Runtime image digest
- Environment name and residency zone
- Budget and limits
- Feature flags

Secrets, access tokens, raw credentials, and hidden reasoning are excluded.

---

## 21. Corrected QA, validation, and acceptance design

### 21.1 Four distinct assurance layers

1. **Structural validation:** schemas, references, hashes, path rules, and contracts.
2. **Deterministic verification:** tests, linters, scans, calculations, policy checks, and reproducible commands.
3. **Agentic review:** interpretation, completeness review, contradiction analysis, and proposal of remediation.
4. **Human acceptance:** accountable approval where policy requires it.

No layer may impersonate another.

### 21.2 Test execution contract

A `TestCase` specifies its executor:

```yaml
type: test_case
id: TC-001
executor:
  tool_id: test.pytest
  tool_version: 1.0.0
  command_profile: unit-default
  timeout_seconds: 300
  network_access: denied
expected:
  exit_code: 0
  evidence:
    - junit_xml
```

The tool runner executes in a sandbox and writes a signed or hashed `TestEvidence` record. The QA agent receives the test case, evidence, acceptance criteria, and produced artifact, but cannot alter the tool result.

For inherently qualitative tests, the test case may specify `executor.type: agentic_review`, with a versioned rubric, reviewer capability, minimum evidence requirements, and human escalation threshold.

### 21.3 Rework semantics

- Validation failure before side effects does not consume a business rework attempt.
- Transient infrastructure retry increments `technical_retry_count`, not `qa_rework_count`.
- QA rejection increments `qa_rework_count` and creates a new `attempt_id`.
- A changed SPOC or materially changed input produces a new run.
- Budget is accounted both per attempt and cumulatively per run.
- Previous failed artifacts and evidence remain immutable and linked.
- The new attempt works from a copy or successor artifact, not by overwriting accepted evidence.

### 21.4 Acceptance conflicts

If deterministic evidence and an agentic review disagree:

- A deterministic critical failure blocks acceptance.
- A deterministic warning can proceed only according to policy.
- An agentic critical finding triggers remediation or human adjudication.
- Human approval cannot silently erase failed evidence. Any override is a separate, reasoned, scoped, expiring policy exception.

---

## 22. Eventing, consistency, and audit implementation

### 22.1 Event authority

Recommended implementation pattern:

1. Business state change and event record are committed in one database transaction.
2. A transactional outbox publishes the event to SSE/stream consumers.
3. A run-evidence projector appends the canonical redacted event representation to `events.jsonl` on the run branch or artifact store.
4. A reconciler detects unpublished or unprojected events.
5. Finalization hashes the ordered event stream and stores the hash in the run summary.

If JSONL is selected as the authority instead, the ADR must explain atomicity, concurrency, query performance, and recovery. The implementation may not casually dual-write.

### 22.2 Event semantics

Every event includes:

- Schema version
- Event ID
- Aggregate type and ID
- Aggregate version
- Run, attempt, step, and correlation IDs
- Causation ID
- Actor identity and authentication context reference
- Policy decision ID where applicable
- UTC timestamp from injected clock
- Event type
- Redacted payload
- Classification
- Result
- Error code where applicable
- Integrity hash

Events are ordered per aggregate by monotonically increasing aggregate version. Global ordering is not assumed.

### 22.3 Redaction and evidence tiers

Define three views:

- Operational event: enough detail for runtime operations.
- Audit event: stable, integrity-protected, redacted record.
- Debug trace: higher detail, short retention, restricted access.

Prompts and model responses are not automatically copied into the audit event. Their storage is classification- and retention-dependent.

---

## 23. Repository, artifact, and concurrency refinements

### 23.1 Stable IDs over paths

Relations resolve through an ID index. File paths are current locations, not identities. A rename changes the ID index projection but not links. Duplicate IDs are hard errors.

### 23.2 Artifact descriptors

Large or binary artifacts use an OKF descriptor:

```yaml
type: artifact_descriptor
id: ART-001
media_type: application/pdf
storage:
  scheme: object_store
  object_key: projects/PRJ-001/sha256/...
content_hash: sha256:...
size_bytes: 12345
malware_scan:
  status: clean
  scanner_version: "..."
provenance:
  run_id: run_...
```

Thresholds are configuration decided in ADR-018.

### 23.3 Branch and merge strategy

- Default branch unit: one logical run branch, retained across technical retries and QA rework attempts.
- Child runs normally contribute through the parent workspace unless isolation policy requires a child branch.
- Before finalization, rebase or merge the latest protected base into the run branch in a controlled step.
- If touched paths changed on the base, run input-hash and semantic-conflict checks again.
- Generated indexes and graph projections are rebuilt after integration, not manually merged.
- A merge conflict is a typed `stale_workspace` condition, not a generic tool failure.
- Accepted outputs cannot be overwritten by a later run without a `supersedes` relation or approved change workflow.

### 23.4 Multi-repository compatibility

Each release publishes a compatibility manifest:

```yaml
platform_version: 1.1.0
agent_repository: 1.1.0
supported_template_versions: ">=1.0.0,<2.0.0"
supported_project_schema: [project/1.0]
supported_spoc_schema: [spoc/1.1]
supported_workflow_contracts: [requirement-to-delivery/1.2]
```

A dedicated integration fixture pins all three repositories and runs the vertical slice. Dependabot-like updates may propose version changes, but compatibility CI must pass before merge.

---

## 24. Additional milestones required

### M0.6: Build-versus-reuse spike

**Deliverables**

- `plan/research/build_vs_reuse_matrix.md`
- One minimal proof per shortlisted orchestration/runtime option using the same atomic SPOC
- Decision record ADR-022

**Evaluation dimensions**

- Durable pause/resume
- Human approval
- State model
- Agent and tool abstraction
- Local/self-hosted deployment
- Identity and policy integration
- Observability
- Cost controls
- Framework lock-in
- License and support
- Migration effort

**Definition of done**

- The chosen first implementation has an explicit rationale and fallback strategy.
- Rejected options are documented without assuming unsupported capabilities.

### M1.10: Project goal, outcome, milestone, and alignment schemas

**Deliverables**

- `project.schema.json`
- `outcome.schema.json`
- `milestone.schema.json`
- Charter, outcome, success-criteria, scope, and milestone templates
- Alignment validator

**Definition of done**

- An executable SPOC with no valid alignment fails full validation.
- A draft work item can be stored with a warning until triage.
- Goal-to-outcome-to-requirement-to-SPOC-to-deliverable traceability is demonstrated in fixtures.

### M1.11: Workflow contract schemas

**Deliverables**

- Workflow registry schema
- Workflow template schema
- Compatibility validator
- Example atomic and requirement-to-delivery workflows

**Definition of done**

- A catalog entry referencing a missing class, incompatible state schema, or incompatible template contract fails validation.

### M1.12: Claim and evidence schema

**Deliverables**

- `claim.schema.json`
- Claim-block Markdown convention
- Evidence reference validator

**Definition of done**

- Status reports are generated from structured claims.
- Each factual project-status claim has one or more evidence references or is explicitly marked as an assumption/opinion.

### M2.6: Team composer

**Deliverables**

- `team_composer.py` separated from individual agent scoring
- Set-cover style deterministic baseline
- Constraints for segregation of duties, maximum team size, and distinct QA actor

**Definition of done**

- The smallest eligible team is selected deterministically.
- A lower-scoring but policy-compliant team is preferred over a higher-scoring policy-incompatible team.

### M3.0: Application ports and architecture tests

This milestone must precede M3.1.

**Deliverables**

- Ports listed in section 20.1
- In-memory adapters
- Dependency-injection composition root
- Import-boundary tests

**Definition of done**

- `project_flow.py` imports no concrete DB, Git, API, model-provider, or secrets implementation.

### M3.10: Atomic execution path

**Deliverables**

- Minimal control Flow for `execution_mode: atomic`
- Direct deterministic tool path
- Single-agent task path

**Definition of done**

- A small validation or document-generation SPOC runs without constructing a multi-agent Crew.
- It still receives manifest, policy, budget, events, validation, and finalization.

### M3.11: Workflow visualization and contract test

**Deliverables**

- Generated Flow diagram artifact in CI
- Expected transition snapshot
- Route completeness test

**Definition of done**

- Every router outcome has a listener.
- Terminal and suspended states are explicit.
- Diagram changes require review.

### M4.6: Artifact quarantine and object-store adapter

**Deliverables**

- ObjectStore port implementation
- Quarantine state
- Malware-scanning hook
- Size/media-type policy

**Definition of done**

- Unscanned or failed-scan binaries never become consumable project inputs.

### M5.6: Approval integrity and segregation of duties

**Deliverables**

- Versioned approval subject hash
- Approver eligibility policy
- Stale-approval invalidation
- Dual-control option

**Definition of done**

- Changing the artifact, manifest, or approval-relevant policy invalidates the approval.
- The originating agent or service identity cannot satisfy a human approval.

### M5.7: Model fallback and provider resilience

**Deliverables**

- Model capability matrix
- Fallback chains
- Circuit breaker and provider health
- Classification-safe fallback policy

**Definition of done**

- Fallback never changes data residency, classification allowance, or required model features.

### M6.6: Transactional outbox and event reconciliation

**Deliverables**

- Outbox schema and publisher
- Evidence projector
- Reconciliation job and CLI

**Definition of done**

- Injected failures between state commit, stream publication, and JSONL projection are recovered without event loss or duplication.

### M6.7: API security and abuse controls

**Deliverables**

- Request and upload size limits
- Per-project quotas
- Rate limiting
- Problem Details error schema
- Endpoint authorization matrix
- Security headers and CORS policy

**Definition of done**

- Every endpoint has positive and negative authorization tests.
- Oversized requests, invalid content types, and cross-project access are rejected and logged.

### M8.6: Supply-chain security

**Deliverables**

- SBOM
- Dependency and container scanning
- Artifact signing/attestation
- License policy
- Base-image update policy

**Definition of done**

- A release is blocked by configured critical supply-chain violations unless a documented expiring exception exists.

### M8.7: Privacy and retention enforcement

**Deliverables**

- Automated retention jobs
- Legal-hold mechanism if required by inception decisions
- Deletion/tombstone semantics
- Evaluation-data classification

**Definition of done**

- Retention is tested, not merely documented.
- Deletion does not break graph integrity silently; tombstones preserve non-sensitive referential history where policy allows.

### M9.8: Accessibility and large-graph performance

**Deliverables**

- Keyboard navigation and accessible graph alternatives
- Paginated/list alternative to graph view
- Graph clustering and lazy loading
- Performance budget

**Definition of done**

- Core project navigation works without relying solely on color or pointer interactions.
- Large fixture projects remain usable under the agreed measured performance budget.

---

## 25. Revised sequencing and release slices

### Slice A: Governed file model

Includes M0.1 through M1.12. Produces no real agent execution. Exit evidence:

- Project with explicit goal/outcomes
- Valid SPOCs in all execution modes
- Stable ID index
- Workflow contracts
- Full validation CI

### Slice B: Deterministic dispatch and atomic execution

Includes M2.1 through M3.2, M3.0, and M3.10. Exit evidence:

- Deterministic matching
- Atomic SPOC execution using fake model/tool adapters
- Complete manifest fingerprint
- Run/attempt identities

### Slice C: Local multi-agent vertical slice

Includes remaining Phase 3 milestones using local or in-memory ports. Exit evidence:

- Bounded Crew execution
- QA evidence separation
- Pause/resume in local mode
- Immutable event evidence

### Slice D: Hardened repository and governance

Includes Phases 4 and 5 plus M4.6, M5.6, and M5.7. Exit evidence:

- Secure file/object storage
- Git branch workflow
- Policy and approval integrity
- Budget and provider controls

### Slice E: Shared multi-project platform

Includes Phase 6 plus M6.6 and M6.7. Exit evidence:

- Shared DB and selected worker platform
- Project isolation
- Transactional event publication
- API security

### Slice F: Project lifecycle MVP

Includes Phase 7. Exit evidence:

- One reference project from intake to closure
- Goal alignment
- Change and risk handling
- Structured evidence-based status reporting

### Slice G: Production readiness

Includes Phase 8, M8.6, and M8.7. Exit evidence:

- Defined SLOs and metric formulas
- Evaluation gates
- Tested recovery and retention
- Signed release artifacts

### Slice H: Human interface

Includes Phase 9 and M9.8. Exit evidence:

- Policy-respecting UI
- Accessible knowledge navigation
- Evidence-grounded PM chat

### 25.1 Parallelization after correction

Safe parallel tracks:

- Schema profiles, graph generator, and reference fixtures after base OKF schema stabilizes.
- Registry loaders and workflow-contract validator after registry schemas stabilize.
- Security threat-test corpus while application ports are developed.
- Frontend component design against generated OpenAPI only after endpoint contracts stabilize.

Unsafe parallelization:

- Building the production Flow before run identity, ports, and checkpoint authority are decided.
- Building hardened Git tools before artifact and branch semantics are decided.
- Building approval UI before approval subject/version semantics exist.
- Training or tuning agent prompts before capability evaluations and deterministic validators exist.

---

## 26. Enhanced phase-boundary checklist

In addition to section 15, every phase boundary must verify:

### Architecture

- No dependency-rule violation.
- ADRs required for the phase are accepted.
- New framework-specific behavior is behind an adapter.
- Source-of-truth ownership for every new state item is documented.

### Security

- Threat model updated for new trust boundaries and tools.
- Positive and negative authorization tests exist.
- Secrets and confidential payloads are absent from normal logs.
- New external destinations are allowlisted and documented.
- Tool side effects have idempotency or reconciliation behavior.

### Data and artifacts

- IDs are stable and unique.
- Schema migration impact is documented.
- Binary/large artifacts follow descriptor and scanning policy.
- Generated projections regenerate without diff.
- Retention and classification are assigned.

### Runtime

- Run, attempt, step, child-run, and tool-call IDs are present where relevant.
- Checkpoint/resume behavior is tested at each new suspension point.
- Cancellation and timeout behavior is tested.
- Budget accounting includes failed and delegated calls.
- No retry can repeat an irreversible side effect without idempotency proof.

### Quality

- Deterministic evidence is separated from agentic interpretation.
- Evaluation fixtures contain expected and prohibited behavior.
- False-positive and false-negative cases exist for critical validators.
- Human override creates explicit exception evidence.

### Operations

- Metrics have formulas, units, labels, and owner.
- Alert has a linked runbook.
- Migration has rollback or forward-fix procedure.
- Failure injection covers newly introduced dependencies.
- Support staff can diagnose a failed run without accessing hidden reasoning.

### Product usability

- Atomic tasks remain simple to create and execute.
- User-visible errors identify what can be corrected without exposing internals.
- Project goal alignment is visible.
- Evidence links resolve by stable ID.
- Accessibility requirements are considered for new UI behavior.

---

## 27. Final implementation directive

The implementation may begin with M0.1, M0.2, and M0.6, followed by the expanded Phase 1. Do not start the production CrewAI Flow until ADR-011 through ADR-015 are accepted and M3.0 is complete. The first executable feature should be an `atomic` SPOC under the same governance envelope planned for larger workflows. This proves manifest compilation, identity, policy boundaries, event evidence, and validation without prematurely introducing multi-agent complexity.

The platform's differentiated value remains the project-governance layer: explicit goals and outcomes, governed SPOCs, capability-based assignment, stable project knowledge, evidence, acceptance, and controlled reuse. Workflow durability, model access, Git hosting, execution sandboxes, queues, and observability should be reused or integrated where existing components meet the documented requirements.
