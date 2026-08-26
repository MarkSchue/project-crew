# Project Manager Handbook

How to run a project on the CrewAI multi-agent delivery platform: set up
a project, author work, add agents, follow the stage gates, and find your
way around the knowledge graph.

> This handbook describes the **current implemented state** of the
> platform (vertical slice through Phase 9). Where a feature is planned
> but not yet built, it is called out explicitly.

---

## 1. The system in one paragraph

Projects are described by **OKF** ("Open Knowledge Format") — plain
Markdown files with YAML front matter, kept in Git. That Markdown is the
**system of record**: requirements, user stories, test cases, decisions,
risks, deliverables, and the run/QA evidence all live as readable files.
A control plane compiles small, governed work packages ("SPOCs") into
immutable run manifests, executes them through agents, and records an
append-only event log. A knowledge graph and a web UI are projections on
top of those files — you can read everything in VS Code without the UI.

Three repositories make up the platform:

| Repository | Role |
|---|---|
| `agent-repository` | Reusable code, the CLI (`mas`), and the **registry** of agents/capabilities/tools/workflows. |
| `project-template-repository` | The JSON Schemas, workflow templates, and the `project_skeleton/` used to create new projects. |
| `active-project-repo` | One **project instance**: its `project.yaml`, `public/` knowledge, `logs/`, and generated indexes. |

---

## 2. Quick start

Prerequisites: Python 3.11+, Git, and `uv` (or `pip`).

```bash
# 1. Install the platform CLI (once)
cd agent-repository
source .venv/bin/activate        # or create one: python3 -m venv .venv
pip install -e ".[dev]"

# 2. Start the control plane (serves the REST API + the web UI)
uvicorn agent_platform.api.main:app
# open http://127.0.0.1:8000/  → sign in with the bearer token (dev default: dev-token-admin)
```

The web UI has six screens: **Overview**, **SPOC editor**, **Runs**,
**Approvals**, **Registry**, and **Knowledge graph**, plus a **Project
Manager chat** panel (bottom-right) on every screen.

To run against a specific project, point the server at it:

```bash
AGENT_PLATFORM_PROJECT_DIR=/path/to/active-project-repo uvicorn agent_platform.api.main:app
```

---

## 3. Creating a new project

```bash
# Create a project from the pinned template skeleton
mas project init ../my-project
```

This copies the `project_skeleton/` (a full `public/` tree, `project.yaml`,
`logs/`, `config/`, `tests/`, etc.) into `../my-project` and writes a
`template.lock` recording the exact template version.

Then edit `my-project/project.yaml` — the minimum project control document:

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
scope: { in_scope: [], out_of_scope: [] }
assumptions: []
constraints: []
charter_ref: public/charter/project_charter.md
```

Validate the project's OKF files at any time:

```bash
mas project validate ../my-project/public          # full lint + cross-reference
mas project validate ../my-project/public --mode fast   # schema only
```

---

## 4. Where the OKF knowledge lives

All project knowledge lives under `public/` in the active project repo.
Each directory holds a different OKF `type`:

| Directory | `type` | What goes in it |
|---|---|---|
| `public/charter/` | `concept` | Project charter, initial constraints |
| `public/requirements/` | `requirement` | Requirements |
| `public/epics/` | `epic` | Epics (clusters of user stories) |
| `public/user_stories/` | `user_story` | User stories (declare `part_of` their epic, `tested_by` test cases) |
| `public/test_cases/` | `test_case` | Acceptance/behavior checks (`validates` back to a story/SPOC) |
| `public/test_results/` | `test_result` | QA results (`pass`/`fail`, `generated_by` the run summary) |
| `public/spocs/` | `spoc` | Governed work packages (`pending/ready/running/review/accepted/rejected`) |
| `public/decisions/` | `architecture_decision` / `decision` | ADRs and project decisions |
| `public/risks/` | `risk` | Risks |
| `public/issues/` | `issue` | Issues |
| `public/dependencies/` | `dependency` | Dependencies (may `blocks` a SPOC) |
| `public/deliverables/` | `deliverable` | Deliverables |
| `public/acceptance/` | `acceptance` | Acceptance strategy/criteria |
| `public/status/` | `status_report` | Status reports (every claim sourced) |
| `public/plans/`, `public/architecture/`, `public/backlog/` | mixed | Plans, architecture constraints, backlog |
| `public/knowledge/` | (generated) | `graph_index.json` — regenerable, never hand-edited |

Run evidence is **not** OKF: `logs/runs/<run-id>/events.jsonl` (raw events)
and `logs/runs/<run-id>/summary.md` (the OKF run summary that links back
to the SPOC and forward to the events).

Every OKF file starts with front matter like:

```yaml
---
schema_version: okf/1.1
id: US-001
type: user_story
title: "First user story"
status: ready
classification: internal
owner: pm
created_at: 2026-08-24T09:00:00Z
updated_at: 2026-08-24T09:00:00Z
tags: []
source_refs: []
relations:
  - type: part_of
    target: EPIC-001
  - type: tested_by
    target: TC-001
provenance:
  created_by_type: human
  created_by_id: pm
  run_id: null
---
```

**Relation vocabulary** (the important ones):

| Relation | Direction | Meaning |
|---|---|---|
| `part_of` | user_story → epic | The story belongs to an epic |
| `tested_by` | user_story → test_case | The story is covered by a test |
| `validates` | test_case → user_story/spoc | The test checks that item |
| `produces` | test_case → test_result | The test produced a result |
| `generated_by` | run_summary/test_result → spoc/run_summary | Provenance |
| `evidenced_by` | → `events.jsonl` | Link to raw log evidence |
| `blocks` | dependency → spoc | A dependency blocks execution |

`mas project validate` fails on dangling relations (a `relations[].target`
that does not resolve to a known `id`) — that is how traceability stays
honest.

---

## 5. Project lifecycle (stage gates)

The platform walks a project through gates (masterplan §8.2):

| Gate | Meaning | Typical artifacts |
|---|---|---|
| **G0** | Intake | Charter, initial constraints |
| **G1** | Charter approved | Decision rights |
| **G2** | Plan baselined | WBS/milestones, epic + tested user stories, risks, dependencies, acceptance strategy |
| **G3** | Build authorized | Compiled, approved SPOCs begin execution |
| **G4** | Release accepted | Passing test results, human acceptance |
| **G5** | Closure approved | Handover; lessons promoted only with approval |

Workflow templates for these (intake, planning baseline, change request,
risk escalation, requirement-to-delivery, closure) live in
`project-template-repository/workflows/`.

---

## 6. Setting up a new agent

Agents live in the registry: `agent-repository/registry/agents/<agent_id>/`
(see §8 for where the registry actually sits today).

```bash
# 1. Scaffold a schema-valid DRAFT agent
mas agent scaffold my_new_agent --registry registry
```

This creates `registry/agents/my_new_agent/` with:

- `agent.yaml` — role, goal, capabilities, allowed tools, delegation, health.
- `prompt.md` — the system prompt.
- `tests/evaluation_fixture.yaml` — evaluation cases (to be filled in).
- `private_knowledge/index.md` — private knowledge index.

The scaffold is intentionally **incomplete** (`status: draft`, `role` and
`goal` are `TODO`). Fill in:

1. `role` and `goal` (remove the `TODO` markers).
2. `capabilities` — list capability ids from the capability catalog
   (§8) with a `proficiency` and `evidence_refs`.
3. `allowed_tools` — only the tools this agent may use.
4. `allowed_classifications` — e.g. `[public, internal]`.
5. `delegation` — whether it may delegate, and to which capability prefixes.
6. `health.evaluation_suite` + `health.minimum_pass_rate`.
7. Add a capability evaluation dataset under `tests/evaluation/<capability_id>/dataset.yaml`.

Then set `status: active`. **Activation is gated**: `mas registry validate`
(and CI) fail on `TODO` role/goal, missing capability evidence, or a missing
`evaluation_suite` — a draft agent cannot be activated until a human fills
these in. The standing **Project Manager agent** (`project_manager_agent`)
is an example of a completed entry.

Validate the whole registry:

```bash
mas registry validate registry --schemas ../project-template-repository/schemas
```

---

## 7. Authoring and running work (SPOCs)

A **SPOC** (Supplier-Procedure-Output-Consumer contract) is the smallest
governed unit of execution. It declares inputs, the procedure
(capabilities, constraints, prohibitions), the outputs, and the consumer.

The easiest way to author one is the web UI **SPOC editor**:

1. Open **SPOC editor**, edit the JSON sample.
2. Click **Validate (client)** — it validates against the *same*
   `spoc.schema.json` the backend uses (no schema drift).
3. Click **Validate (backend)** for the authoritative check.

A minimal SPOC:

```json
{
  "schema_version": "spoc/1.1",
  "id": "SPOC-DEMO-001",
  "type": "spoc",
  "title": "Demo SPOC",
  "status": "draft",
  "project_id": "PRJ-001",
  "owner": "pm",
  "created_at": "2026-08-26T09:00:00Z",
  "classification": "internal",
  "workflow": "requirement_to_delivery@1.2.0",
  "supplier": { "provided_by": "product_owner", "inputs": [ { "ref": "public/user_stories/US-001.md", "required": true } ] },
  "procedure": { "objective": "demo", "explicit_capabilities": ["architecture.solution_documentation"] },
  "output": {
    "artifacts": [ { "target": "public/deliverables/DEL-DEMO.md", "schema": "okf/1.1", "required": true } ],
    "acceptance_criteria": [ { "id": "AC-1", "statement": "accepted", "validator": "traceability_validator" } ]
  },
  "consumer": { "next_role": "qa_agent", "on_success": "request_human_approval", "on_reject": "return_to_originating_agent" },
  "retry_policy": { "max_attempts": 2, "retry_on": ["schema_validation_error"] }
}
```

Compilation and execution run through the control plane (REST API / UI),
not a `mas spoc` command (the masterplan's `mas spoc *` / `mas run *`
commands are not yet implemented). The run lifecycle is visible under
**Runs**; a run's state machine is
`draft → validated → ready → leased → running → review → accepted → closed`,
with `rejected`/`dead_letter`/`cancelled` as exits.

---

## 8. The registry (agents, capabilities, tools, workflows)

| Path | Contents |
|---|---|
| `registry/capabilities/capability_catalog.yaml` | Capability ids, risk level, dependencies |
| `registry/agents/<id>/agent.yaml` + `prompt.md` | Agent definitions |
| `registry/tools/<tool_id>/tool.yaml` | Tool contracts (permissions, side effects, retry) |
| `registry/workflows/<id>/<version>.yaml` | Workflow implementation bindings |
| `registry/models/`, `registry/skills/` | Model catalog, skills |

> **Current working location:** the populated registry in this vertical
> slice lives at `agent-repository/tests/fixtures/registry/`. The dev
> server loads `agent-repository/registry/` when it exists, otherwise it
> falls back to the fixture registry. Set `AGENT_PLATFORM_REGISTRY_DIR` to
> point at a different registry.

---

## 9. QA, acceptance, and evidence

- A **user story** must declare at least one `tested_by` relation
  (`mas project validate` flags untested stories).
- A **test case** declares `validates` back to the story/SPOC.
- QA execution produces a **test result** (`type: test_result`, `status:
  pass` or `fail`) with `generated_by` the run summary and `evidenced_by`
  the `events.jsonl`.
- A requirement is **covered** only when every `tested_by` test case has at
  least one linked test result, and **currently passing** only when its
  most recent result is a pass.

The QA rework loop sends a rejected SPOC back to the originating agent
(bounded by `retry_policy.max_attempts`), then escalates to a human.

---

## 10. Knowledge graph, documents, and the PM chat

Regenerate the graph projection (and run it in CI):

```bash
mas graph rebuild ../active-project-repo
# output: public/knowledge/graph_index.json
```

In the web UI:

- **Knowledge graph** renders every node colored by `type` with a legend,
  search, and type filter. Click any node to open its **document viewer**
  (front matter + body + relations as clickable links).
- **Project Manager chat** (bottom-right, every screen) answers read-only
  questions about project state and cites the OKF `id` of every artifact
  it uses — click a citation to open that artifact. It can read
  `public`/`internal` only; it never writes or approves.

---

## 11. Approvals

Consequential actions require human approval (they cannot be auto-approved
by agents). Mandatory-approval actions include scope/budget/baseline
changes, access expansion, policy exceptions, production changes,
knowledge promotion, and agent/tool activation. See the **Approvals**
screen in the UI for the inbox; resolution requires an explicit human
decision (an expired approval blocks progress and cannot later be
approved).

---

## 12. CLI reference

| Command | Purpose |
|---|---|
| `mas project init <dir>` | Create a new project from the template skeleton |
| `mas project validate <dir> [--mode fast\|full] [--schemas dir]` | Lint + cross-reference OKF files |
| `mas project migrate <dir>` | Apply pending project migrations |
| `mas index rebuild <dir>` | Regenerate per-directory `index.md` |
| `mas graph rebuild <dir> [--style-config f]` | Regenerate `public/knowledge/graph_index.json` |
| `mas registry validate <registry-dir> [--schemas dir]` | Validate agents/capabilities/tools/workflows |
| `mas agent scaffold <agent-id> [--registry dir]` | Scaffold a draft agent |
| `mas chat [--question q] [--graph f] [--project-root dir]` | Ask the Project Manager agent |
| `mas docs validate` / `mas docs coverage` | Check documentation-as-code mapping/coverage |

---

## 13. Troubleshooting

- **`mas` not found** → activate the venv and `pip install -e ".[dev]"`.
- **Validation fails on a relation** → the `target` id must exist in the
  same project and be type-compatible (see §4 table).
- **Graph rebuild fails** → a node's `type` has no style entry, or a
  relation is dangling; fix the OKF file.
- **Agent won't activate** → fill the `TODO` role/goal, add capability
  `evidence_refs`, and declare `health.evaluation_suite`.
- **Chat refuses an answer** → it may be asking for `confidential`/
  `restricted` data (denied by default), or the graph has no grounded
  evidence (it says so rather than fabricating).
