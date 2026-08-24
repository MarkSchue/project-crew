# Implementation Plan: CrewAI Multi-Agent System for Project Delivery

**Document status:** Detailed implementation plan derived from the masterplan
**Source of truth:** `plan/crewai_multi_agent_project_masterplan.md` (all section references below point there)
**Audience:** A coding agent or software engineering team executing the build
**Primary framework:** CrewAI
**Document version:** 1.0
**Date:** 2026-08-24

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
