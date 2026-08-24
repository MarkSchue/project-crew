# Masterplan: CrewAI Multi-Agent System for Project Delivery

**Document status:** Revised target architecture and implementation plan  
**Language of source requirements:** German  
**Implementation target:** A coding agent or software engineering team  
**Primary framework:** CrewAI  
**Document version:** 1.0  
**Date:** 2026-08-22

---

## 1. Executive summary

The system is a file-first, auditable, capability-driven multi-agent platform for running projects. It combines deterministic project governance with flexible agent collaboration. CrewAI is used as the runtime for agents, tasks, crews, and flows, but project state, contracts, decisions, and knowledge remain framework-independent and are persisted in repositories as versioned artifacts.

The architecture is based on three strictly separated repositories:

1. **Agent Repository:** reusable agent definitions, capabilities, skills, tools, policies, runtime adapters, and global knowledge.
2. **Project Template Repository:** project-independent blueprints, governance rules, schemas, workflow templates, quality gates, and compliance packs.
3. **Active Project Repository:** requirements, SPOCs, project knowledge, decisions, deliverables, logs, and isolated private workspaces for one concrete project.

The core execution contract is the **SPOC**, meaning Supplier, Procedure, Output, Consumer. Every executable project assignment is represented by one versioned SPOC. The system validates the SPOC, derives required capabilities, selects a primary agent and optional specialist agents, resolves tools and knowledge access, executes a CrewAI Flow, validates outputs, requests human approval when required, writes an immutable run record, and proposes a Git commit or pull request.

The system should not begin as a fully autonomous project manager. The first production-capable release should focus on controlled execution of bounded work packages with explicit inputs, schemas, approval rules, quality gates, retry limits, budget limits, and traceability. Autonomy can be increased only after reliability metrics demonstrate that the controls work.

---

## 2. Purpose, goals, and non-goals

### 2.1 Purpose

Create an enterprise-grade multi-agent engine that can operate projects from requirements through planning, execution, review, and delivery while keeping humans in control of consequential decisions.

### 2.2 Business goals

- Convert project requirements into traceable, executable work packages.
- Reuse specialized agents, skills, tools, and governance across projects.
- Preserve project knowledge in a navigable, machine-readable format.
- Represent essentially all project outcomes, inputs, and evidence as linked OKF Markdown files, so that a web UI can render them as one navigable knowledge graph.
- Provide a web UI that lets users jump between related artifacts, for example from a project outcome to the SPOC that produced it, the run that executed it, and the log or evidence file behind that run, with each document type visually distinguished.
- Always make a Project Manager agent available for conversational questions about project state, risks, blockers, and progress, grounded in the same evidence used by the graph and reports.
- Make every material agent action explainable and auditable.
- Allow project teams to work in VS Code and Git without depending on a proprietary user interface.
- Enable later introduction of a web interface without changing the storage model.
- Support different LLMs at platform, agent, workflow, or SPOC level.
- Separate public project knowledge from agent-specific confidential working data.
- Allow controlled creation and onboarding of new agents during a project.

### 2.3 Technical goals

- Use CrewAI Flows as the durable orchestration boundary.
- Use Crews for bounded collaborative work inside flow steps.
- Use typed state and structured outputs wherever possible.
- Keep repository artifacts as the system of record.
- Make execution restartable and idempotent.
- Enforce least-privilege access for agents and tools.
- Provide deterministic validation before and after LLM execution.
- Support local development and later containerized deployment.

### 2.4 Non-goals for the initial release

- Fully autonomous portfolio management.
- Unrestricted self-modifying agents.
- Direct production changes without approval.
- Storing secrets in Markdown, YAML, Git, prompts, or agent memory.
- Treating free-form agent conversation as authoritative project state.
- Building a complex web user interface before the headless runtime is reliable.
- Supporting every project methodology in the first release.
- Replacing established ticketing, CI/CD, document management, or identity systems.

---

## 3. Revision of the initial Gemini plan

The initial plan contains useful concepts, especially the three-repository topology, OKF, SPOCs, capability matching, private workspaces, model overrides, and audit logging. It is not yet implementation-ready for the following reasons.

### 3.1 Missing separation between control plane and execution plane

The original design mixes registry management, matching, execution, API operations, and repository mutation. The revised design separates:

- **Control plane:** registry, policy, capability catalog, model routing, workflow catalog, approvals, and run metadata.
- **Execution plane:** isolated worker process that reads a resolved execution package and runs a CrewAI Flow.

This separation reduces accidental privilege escalation and simplifies testing.

### 3.2 Markdown is not sufficient as the only runtime database

Markdown is excellent for human-readable project knowledge, but runtime locking, idempotency, leases, streaming events, and concurrent updates require transactional state. The revised design uses:

- Git and OKF Markdown as the authoritative project record.
- SQLite for local development and PostgreSQL for shared deployment as operational state stores.
- Append-only JSONL events for portable run evidence.

The database is operational, not the sole system of record.

### 3.3 Capability matching must be deterministic before it is semantic

A matching LLM must not be the sole authority for agent assignment. The revised matcher uses four stages:

1. Validate explicit capabilities from the SPOC.
2. Expand aliases and dependencies from the capability registry.
3. Optionally extract additional candidate capabilities from procedure text.
4. Apply deterministic scoring, policy filters, permissions, cost, health, and availability.

Any LLM-derived capability is marked as inferred and can trigger approval.

### 3.4 Agent-as-a-tool requires strict limits

Wrapping arbitrary agents as tools can create recursive delegation, hidden costs, and unclear accountability. The revised design allows delegation only through a controlled `AgentDelegateTool` with:

- Maximum delegation depth.
- Maximum child calls.
- Allowed capability list.
- Explicit input and output schema.
- Independent run IDs.
- Budget and token ceilings.
- No implicit file access.
- Complete parent-child audit linkage.

### 3.5 Audit logs need structured events, not only one Markdown file

A single shared `log.md` is susceptible to merge conflicts and is difficult to query. The revised system writes one append-only event stream per run and generates human-readable Markdown summaries and indexes. Raw events are never edited after completion.

### 3.6 Security boundaries must be enforced by tools

Directory conventions alone do not protect private data. File tools must resolve canonical paths, reject symbolic-link escapes, enforce route-specific allowlists, redact secrets, and label every read and write. The execution container should mount only approved paths.

### 3.7 Missing project lifecycle model

The revised design introduces project phases, stage gates, baselines, change control, risks, issues, decisions, dependencies, and acceptance records. This is necessary if the system is to run projects rather than merely execute isolated tasks.

### 3.8 Missing operational controls

The revised design includes retries, dead-letter handling, cancellation, timeouts, budget enforcement, human approvals, resumability, health status, telemetry, and incident procedures.

---

## 4. Architectural principles

1. **Files are durable knowledge; databases are operational state.**
2. **Flows orchestrate; agents reason; tools act.**
3. **Every action has a contract, identity, authorization, and evidence.**
4. **Deterministic checks surround probabilistic execution.**
5. **No agent receives broader access than its task requires.**
6. **Outputs are drafts until validated and accepted.**
7. **Git history is not a substitute for execution telemetry, and telemetry is not a substitute for Git history.**
8. **Policies override prompts.**
9. **Human approval is a first-class workflow state, not a chat convention.**
10. **Agent creation is governed change management.**
11. **Model routing is explicit, testable, and cost-controlled.**
12. **Knowledge provenance is mandatory.**
13. **Project artifacts remain usable without CrewAI.**
14. **The platform must fail closed for authorization and fail safely for execution.**
15. **Autonomy increases only when measured reliability supports it.**

---

## 5. Target system context

### 5.1 Primary actors

- Project sponsor
- Project manager
- Product owner or business owner
- Domain subject-matter experts
- Security, legal, compliance, architecture, and finance reviewers
- Platform administrator
- Agent developer
- Coding agent
- CrewAI runtime agents
- External systems through approved MCP servers or native tools

### 5.2 Core use cases

- Bootstrap a new project from a governed template.
- Ingest and normalize requirements.
- Build a work breakdown structure.
- Create and approve SPOCs.
- Match work to agents and tools.
- Execute analysis, design, documentation, coding, testing, and review work.
- Maintain risks, issues, actions, decisions, and dependencies.
- Generate status reports from evidence.
- Escalate blocked or high-risk work to humans.
- Validate deliverables against acceptance criteria.
- Capture reusable lessons without leaking project-confidential data.
- Navigate the project knowledge graph from any artifact to its related requirements, decisions, risks, runs, and log evidence.
- Ask the Project Manager agent about current project state, at-risk items, or the provenance of any artifact, at any time.

---

## 6. Logical architecture

```text
Human / VS Code / Future Web UI
              |
              v
        API and CLI Layer
              |
              v
        Control Plane
  + registry and policy resolver
  + SPOC compiler and validator
  + capability matcher
  + model and budget router
  + approval service
  + run coordinator
              |
       resolved run package
              |
              v
        Execution Plane
  + CrewAI Flow
  + bounded Crews and Tasks
  + agent delegation tool
  + repository and MCP tools
  + validators and quality gates
              |
              v
 Storage and Evidence Layer
  + three Git repositories
  + operational database
  + event and artifact storage
  + secrets manager
  + observability backend
```

### 6.1 Control plane responsibilities

- Parse and validate project and SPOC files.
- Resolve versioned template references.
- Resolve agent, skill, tool, and model dependencies.
- Enforce policy before execution.
- Create immutable run manifests.
- Acquire work leases and idempotency locks.
- Dispatch execution.
- Manage cancellations, approvals, retries, and escalations.
- Persist status transitions.

### 6.2 Execution plane responsibilities

- Load only the resolved run package.
- Execute the selected CrewAI Flow.
- Call approved tools with scoped credentials.
- Produce typed outputs and evidence.
- Emit structured events.
- Never mutate registry or governance policy directly.

### 6.3 Storage responsibilities

- Git repositories store versioned definitions and project artifacts.
- Operational database stores queues, leases, state, approval records, and indexes.
- Object storage may hold large artifacts, with hashes and metadata committed to Git.
- Secret storage provides ephemeral credentials to approved tools.

---

## 7. Three-repository topology

### 7.1 Repository A: `agent-repository`

```text
agent-repository/
├── README.md
├── pyproject.toml
├── uv.lock
├── src/agent_platform/
│   ├── control_plane/
│   │   ├── spoc_compiler.py
│   │   ├── capability_matcher.py
│   │   ├── policy_engine.py
│   │   ├── model_router.py
│   │   ├── approval_service.py
│   │   └── run_coordinator.py
│   ├── execution_plane/
│   │   ├── project_flow.py
│   │   ├── crew_factory.py
│   │   ├── task_factory.py
│   │   └── delegate_tool.py
│   ├── registries/
│   ├── repositories/
│   ├── schemas/
│   ├── telemetry/
│   └── security/
├── registry/
│   ├── agents/
│   │   └── agent_id/
│   │       ├── agent.yaml
│   │       ├── prompt.md
│   │       ├── tests/
│   │       └── private_knowledge/
│   ├── capabilities/
│   │   ├── capability_catalog.yaml
│   │   └── capability_aliases.yaml
│   ├── skills/
│   │   └── skill_id/
│   │       ├── skill.yaml
│   │       ├── instructions.md
│   │       └── tests/
│   ├── tools/
│   │   └── tool_id/tool.yaml
│   ├── models/model_catalog.yaml
│   └── workflows/workflow_catalog.yaml
├── tools/
│   ├── file_tools/
│   ├── git_tools/
│   ├── mcp_tools/
│   ├── validation_tools/
│   └── reporting_tools/
├── policies/
│   ├── access/
│   ├── execution/
│   ├── model/
│   ├── data/
│   └── approval/
├── public_knowledge/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── security/
│   └── evaluation/
└── .github/workflows/
```

**Rule:** Agent definitions and reusable code are versioned here. Active project artifacts never live here.

### 7.2 Repository B: `project-template-repository`

```text
project-template-repository/
├── README.md
├── template_manifest.yaml
├── project_skeleton/
│   ├── public/
│   ├── private/
│   ├── logs/
│   ├── config/
│   └── .vscode/
├── schemas/
│   ├── okf.schema.json
│   ├── spoc.schema.json
│   ├── agent.schema.json
│   ├── project.schema.json
│   ├── decision.schema.json
│   ├── risk.schema.json
│   └── run_event.schema.json
├── templates/
│   ├── requirements/
│   ├── epics/
│   ├── user_stories/
│   ├── test_cases/
│   ├── test_results/
│   ├── spocs/
│   ├── decisions/
│   ├── risks/
│   ├── issues/
│   ├── plans/
│   ├── status_reports/
│   ├── acceptance/
│   └── retrospectives/
├── workflows/
│   ├── project_intake.yaml
│   ├── requirement_to_delivery.yaml
│   ├── change_request.yaml
│   ├── risk_escalation.yaml
│   └── project_closure.yaml
├── governance/
│   ├── stage_gates/
│   ├── quality_gates/
│   ├── compliance_packs/
│   └── approval_matrices/
├── examples/
└── tests/
```

**Rule:** A template release is immutable. Projects pin a template version and update through an explicit migration.

### 7.3 Repository C: `active-project-repo`

```text
active-project-repo/
├── README.md
├── project.yaml
├── template.lock
├── config/
│   ├── runtime.yaml
│   ├── access_policy.yaml
│   ├── model_policy.yaml
│   └── quality_policy.yaml
├── public/
│   ├── charter/
│   ├── requirements/
│   ├── epics/
│   ├── user_stories/
│   ├── test_cases/
│   ├── test_results/
│   ├── backlog/
│   ├── spocs/
│   │   ├── pending/
│   │   ├── ready/
│   │   ├── running/
│   │   ├── review/
│   │   ├── accepted/
│   │   ├── rejected/
│   │   └── index.md
│   ├── plans/
│   ├── architecture/
│   ├── decisions/
│   ├── risks/
│   ├── issues/
│   ├── dependencies/
│   ├── deliverables/
│   ├── acceptance/
│   ├── status/
│   └── knowledge/
├── private/
│   ├── agent_id/
│   │   ├── inbox/
│   │   ├── scratch/
│   │   ├── evidence/
│   │   └── outbox/
│   └── shared_restricted/
├── logs/
│   ├── runs/run_id/events.jsonl
│   ├── runs/run_id/summary.md
│   ├── approvals/
│   ├── security/
│   └── index.md
├── artifacts/
│   ├── manifests/
│   └── checksums/
├── scripts/
├── tests/
└── .vscode/
    ├── settings.json
    ├── tasks.json
    ├── extensions.json
    └── mcp.json
```

**Rule:** Public does not mean internet-public. It means accessible to all project agents. Private means explicitly restricted.

---

## 8. Project lifecycle model

### 8.1 States

1. **Proposed**
2. **Initiating**
3. **Planning**
4. **Executing**
5. **Monitoring and controlling**
6. **Closing**
7. **Archived**

### 8.2 Stage gates

- **G0, Intake accepted:** sponsor, objective, owner, classification, and initial constraints exist.
- **G1, Charter approved:** scope, success criteria, funding assumption, governance, and decision rights are approved.
- **G2, Plan baselined:** work breakdown, milestones, dependencies, risks, architecture constraints, and acceptance strategy exist.
- **G3, Build authorized:** critical security, legal, compliance, data, and architecture checks passed.
- **G4, Release accepted:** deliverables passed quality and business acceptance gates.
- **G5, Closure approved:** handover, unresolved items, operational ownership, and lessons learned are recorded.

Each gate is represented by a versioned acceptance artifact and an approval event. Agents may prepare evidence but may not impersonate human approvers.

### 8.3 Work hierarchy

```text
Portfolio or program reference
└── Project
    ├── Outcome
    ├── Milestone
    ├── Epic or workstream
    │   └── User story or requirement
    │       └── Test case(s)
    │           └── Test result(s)
    ├── SPOC work package
    ├── Task execution
    └── Deliverable and acceptance record
```

Every user story or requirement belongs to exactly one epic (`part_of` relation, section 9.3) so the backlog can be browsed and reported epic by epic. Every user story or requirement in turn is validated by one or more test cases (`tested_by` relation), and every test case produces test results over time (`produces` relation). See section 9.7 for the full requirement-to-test traceability model and section 13.5 for the QA rework loop that keeps this chain trustworthy.

---

## 9. Open Knowledge Format, revised

OKF is the common file representation for human-readable knowledge. It is not a substitute for JSON Schema or database consistency.

### 9.1 Mandatory front matter

```yaml
---
schema_version: "okf/1.1"
id: "OKF-ARCH-0001"
type: "architecture_decision"
title: "Use CrewAI Flows as orchestration boundary"
summary: "Flows coordinate durable project execution; Crews perform bounded collaboration."
status: "approved"
classification: "internal"
owner: "project_architect"
created_at: "2026-08-22T08:00:00Z"
updated_at: "2026-08-22T08:00:00Z"
valid_from: "2026-08-22"
review_after: "2026-11-22"
tags: ["crewai", "orchestration"]
source_refs: []
relations:
  - type: "implements"
    target: "REQ-PLAT-001"
provenance:
  created_by_type: "human"
  created_by_id: "project_architect"
  run_id: null
content_hash: "sha256:..."
---
```

### 9.2 Required semantics

- IDs are globally unique inside a project.
- Timestamps are UTC ISO 8601.
- Classification is mandatory.
- Every agent-generated artifact contains a `run_id`.
- Every material factual claim should contain a source reference or be marked as an assumption.
- Relations use controlled vocabulary.
- Files must show status and owner.
- `review_after` triggers staleness checks but does not silently invalidate content.
- Hashes are calculated after canonicalization and excluded from the hash input itself.

### 9.3 Recommended relation vocabulary

- `depends_on`
- `blocks`
- `implements`
- `satisfies`
- `derived_from`
- `supersedes`
- `contradicts`
- `validates`
- `produces`
- `consumes`
- `owned_by`
- `related_to`
- `generated_by` (artifact was produced by a specific run)
- `evidenced_by` (a claim or artifact is backed by a specific log, event, or test result)
- `reports_on` (a status or summary artifact describes another artifact or the project as a whole)
- `part_of` (a user story or requirement is clustered under a specific epic)
- `tested_by` (a requirement, user story, or acceptance criterion is validated by a specific test case)

### 9.4 Index strategy

Each directory has an `index.md` generated from front matter. The index is treated as a projection and can be regenerated. Agents must not use indexes as the only source when the target files are available.

### 9.5 Coverage principle: nearly everything is an OKF file

The knowledge graph and the web UI described in section 21 (Phase 9) are only as complete as the artifacts that carry OKF front matter. The plan therefore treats OKF coverage as close to total, not limited to conceptual knowledge documents:

- Every requirement, user story, SPOC, decision, risk, issue, dependency, deliverable, acceptance record, status report, and retrospective is an OKF Markdown file.
- Every run's human-readable `summary.md` (section 16.3) is also an OKF file, with `relations` linking back to its SPOC and forward to the artifacts it produced and the raw event file it summarizes. This is what allows the UI to jump from an outcome to the log evidence of the run that created it.
- Only genuinely non-narrative data is excluded from OKF: raw `events.jsonl` streams, binary artifacts, checksums, and generated index or graph projections. These are still linked from and to OKF files through `relations` and `source_refs`, so they remain reachable from the graph even though they are not themselves OKF documents.
- A file without valid OKF front matter is treated as a broken graph node by the linter and CI, not as an exception to ignore.

### 9.6 Knowledge graph generation and visual taxonomy

The knowledge graph is a regenerable projection, not a new system of record. A graph generator walks all OKF files in the active project repository, using `id`, `type`, `status`, `owner`, `relations`, `source_refs`, and `cross_references` to build nodes and edges, and writes them to a generated artifact (for example `public/knowledge/graph_index.json`) alongside the existing `index.md` files. Non-OKF evidence such as `events.jsonl` and binary artifacts are included as leaf nodes reachable through `generated_by` and `evidenced_by` edges. The graph index is rebuilt by CI and by an explicit CLI command (section 17.1) and must never be hand-edited.

Each node's `type` maps to a distinct visual style in the web UI so that document kinds are recognizable at a glance:

| OKF `type` | Suggested color | Suggested icon / shape |
|---|---|---|
| `requirement` / `user_story` | blue | document |
| `spoc` | orange | gear |
| `architecture_decision` / decision (ADR) | purple | milestone diamond |
| `risk` | red | warning triangle |
| `issue` | amber | flag |
| `dependency` | grey | link |
| `deliverable` | green | package |
| `acceptance` | teal | check-shield |
| `status_report` | yellow | chart |
| `run_summary` (`summary.md`) | slate | terminal |
| `raw_event` / `events.jsonl` (non-OKF leaf) | light grey, dashed border | log |
| `agent` (registry) | cyan | person/robot |
| `capability` | indigo | puzzle piece |

This table is a starting default and should be captured in an ADR and made configurable, but every rendered node must be styled by its `type`, and a legend must always be visible in the graph view. `epic`, `test_case`, and `test_result` should be added to this table with their own distinct styles (for example epic in dark blue as a folder/cluster shape, test case in brown as a checklist shape, and test result in either green or red depending on pass or fail) so epic clusters and test coverage are visible at a glance.

### 9.7 Requirement, epic, and test traceability

Requirements management is treated as first-class OKF content, not a side artifact:

- **Epics** (`type: "epic"`) live in `public/epics/` and cluster related user stories or requirements. Each epic lists its member user stories through `relations` of type `part_of` (declared on the user story, pointing at the epic) so the relation is owned by the child and the epic node is derived by the graph generator, consistent with the index-as-projection rule in section 9.4.
- **User stories and requirements** (`public/user_stories/`, `public/requirements/`) declare `part_of` their epic and `tested_by` one or more test cases. A user story without at least one `tested_by` relation is flagged by CI as untested backlog, not silently accepted.
- **Test cases** (`type: "test_case"`) live in `public/test_cases/`, restate the acceptance criteria or behavior being checked, and declare `validates` back to the requirement, user story, or SPOC `acceptance_criteria` entry (section 10.2) they cover.
- **Test results** (`type: "test_result"`) live in `public/test_results/`, one file (or one dated entry) per QA execution, with a `produces` relation from the test case and a `pass` / `fail` status in front matter. Test results are also linked with `evidenced_by` to the run's `events.jsonl` and `generated_by` back to the run summary (section 16.3) that produced them, so the graph can be walked from a requirement, to its test case, to every historical result, to the underlying log evidence.
- CI and the graph generator treat a requirement as "covered" only when every `tested_by` test case has at least one linked test result, and as "currently passing" only when its most recent linked result is a pass. Coverage and pass status are surfaced per epic so an epic's health can be read at a glance.

---

## 10. SPOC contract specification

### 10.1 Purpose

A SPOC is the smallest governed unit of project execution. It must be sufficiently complete for an authorized runtime to determine what may be done, by whom, with which inputs, under which constraints, and how success is accepted.

### 10.2 SPOC schema example

```yaml
---
schema_version: "spoc/1.1"
id: "SPOC-2026-0042"
type: "spoc"
title: "Create authentication architecture specification"
status: "ready"
project_id: "PRJ-001"
priority: "high"
owner: "security_workstream_lead"
created_at: "2026-08-22T08:00:00Z"
classification: "confidential"
workflow: "requirement_to_delivery@1.2.0"

supplier:
  provided_by: "product_owner"
  inputs:
    - ref: "public/user_stories/US-001.md"
      required: true
      expected_hash: "sha256:..."
    - ref: "public/architecture/constraints.md"
      required: true

procedure:
  objective: "Create an implementation-ready authentication architecture."
  instructions_ref: "public/plans/auth_procedure.md"
  explicit_capabilities:
    - "security.oauth2.design"
    - "architecture.solution_documentation"
  allow_capability_inference: true
  inferred_capability_approval_threshold: "high_risk"
  constraints:
    max_runtime_seconds: 1800
    max_delegation_depth: 1
    max_child_agent_calls: 3
    max_total_cost_usd: 8.00
    network_access: "allowlisted"
    code_execution: "sandbox_only"
  prohibited_actions:
    - "write_to_production"
    - "modify_access_policy"

output:
  artifacts:
    - target: "public/architecture/authentication_spec.md"
      schema: "okf/1.1"
      required: true
    - target: "public/decisions/ADR-auth-token.md"
      schema: "adr/1.0"
      required: true
  acceptance_criteria:
    - id: "AC-1"
      statement: "All requirements are mapped to design decisions."
      validator: "traceability_validator"
      test_case_refs: ["public/test_cases/TC-AUTH-001.md"]
    - id: "AC-2"
      statement: "No critical security rule violations."
      validator: "security_policy_validator"
      test_case_refs: ["public/test_cases/TC-AUTH-002.md"]

consumer:
  next_role: "qa_agent"
  on_success: "request_human_approval"
  on_reject: "return_to_originating_agent"
  approval_policy: "architecture_and_security"

routing:
  preferred_agent: null
  excluded_agents: []
  model_override: null
  data_residency: "eu"

retry_policy:
  max_attempts: 2
  retry_on: ["transient_tool_error", "schema_validation_error"]
  do_not_retry_on: ["authorization_denied", "budget_exceeded"]
---
```

### 10.3 SPOC state machine

```text
draft -> validated -> ready -> leased -> running
running -> waiting_for_human -> running
running -> review -> accepted -> closed
running -> retry_pending -> leased
running -> blocked
review -> rejected -> ready
any active state -> cancelled
terminal error -> dead_letter
```

State changes require an event containing actor, timestamp, previous state, new state, reason, correlation ID, and version.

The `review -> rejected -> ready` transition is how a negative QA result reaches the originating agent: the SPOC is not closed, ownership returns to `ready` bounded by `retry_policy.max_attempts`, and the QA agent's rejection reason, failing test case IDs, and test result reference are recorded on the transition event so the next attempt starts from documented, evidenced feedback rather than a bare rejection (see section 13.5).

### 10.4 SPOC compiler

The compiler creates an immutable run manifest by:

1. Resolving and hashing all input references.
2. Validating schema and policy.
3. Resolving workflow and template versions.
4. Expanding capability dependencies.
5. Resolving agent, skill, tool, and model versions.
6. Creating file access allowlists.
7. Calculating maximum resource limits.
8. Recording approval requirements.
9. Assigning run and correlation IDs.
10. Signing or hashing the manifest.

No execution starts directly from a mutable SPOC file. It starts from the compiled manifest.

---

## 11. Agent model and registry

### 11.1 Agent definition

```yaml
schema_version: "agent/1.1"
agent_id: "security_architect"
version: "1.3.0"
name: "Security Architecture Agent"
status: "active"
role: "Security architecture specialist"
goal: "Produce traceable and policy-compliant security architecture outputs."
prompt_ref: "registry/agents/security_architect/prompt.md"
default_model_profile: "reasoning_high"
capabilities:
  - id: "security.oauth2.design"
    proficiency: 4
    evidence_refs: ["registry/agents/security_architect/tests/oauth2_eval.yaml"]
  - id: "security.threat_model"
    proficiency: 3
allowed_tools:
  - "repository.read"
  - "repository.write_scoped"
  - "knowledge.search"
  - "security.policy_check"
allowed_classifications: ["internal", "confidential"]
delegation:
  can_delegate: true
  allowed_capability_prefixes: ["security.", "architecture."]
  max_depth: 1
human_escalation:
  mandatory_for: ["policy_exception", "critical_risk"]
health:
  evaluation_suite: "security_architect_regression"
  minimum_pass_rate: 0.90
```

### 11.2 Registry requirements

- Semantic versioning for agents, skills, tools, workflows, and schemas.
- Deprecation and replacement metadata.
- Evaluation evidence for claimed capabilities.
- Explicit data classification limits.
- Tool and model allowlists.
- Owner and review date.
- Runtime health status separate from static definition.
- No secrets in registry files.

### 11.3 New agent creation workflow

1. A need is raised through a governed change request.
2. Existing capabilities and agents are searched first.
3. A scaffold is generated from the agent template.
4. A human owner defines role, goal, restrictions, and capabilities.
5. Prompt and tool permissions undergo security review.
6. Capability-specific evaluations are created.
7. The agent runs in shadow mode on historical test cases.
8. A reviewer approves activation.
9. The registry version is released.
10. The agent is monitored and can be quarantined automatically.

Agents may draft another agent, but may not activate it.

### 11.4 Standing Project Manager agent

Unlike SPOC-bound execution agents, a `project_manager_agent` is a standing, always-available registry agent, one instance per active project, reachable through a persistent chat surface in the web UI (and a `mas chat` CLI command, section 17.1) rather than through a SPOC. It assists the human project manager rather than replacing them.

- **Purpose:** answer questions about project state, such as open risks, blocked work, stage-gate readiness, recent decisions, or the provenance of a specific artifact.
- **Grounding:** it only reads the public project knowledge graph, generated status reports, run summaries, and operational run/approval state exposed by the control plane. It does not use free-form agent memory as a source of truth (principle in section 4).
- **Tool access:** read-only tools only, for example `graph_query_tool`, `artifact_search_tool`, `status_aggregator_tool`, and `run_evidence_reader_tool`. It has no repository write tools, no Git tools, and no delegation rights to execution agents.
- **Classification:** it may read `public` and `internal` artifacts by default; access to `confidential` or `restricted` project data follows the same classification rules as any other agent (section 15.6) and is denied by default.
- **Answer discipline:** every substantive answer cites the OKF `id` of the artifacts it used. If the graph or evidence does not contain an answer, it says so instead of inferring or fabricating one.
- **Sessions:** conversations are session-scoped, logged as run-style events for auditability (section 16), and do not themselves mutate project state. If a user asks it to take an action (for example, approve something), it explains how to do so through the proper approval or execution path instead of performing it directly.

---

## 12. Capability ontology and matching

### 12.1 Capability definition

```yaml
id: "security.oauth2.design"
version: "1.0.0"
description: "Design OAuth2 and OIDC authentication flows."
parent: "security.identity"
aliases: ["oauth_design", "oidc_architecture"]
requires:
  - "architecture.requirement_traceability"
risk_level: "high"
minimum_proficiency: 3
required_evaluations:
  - "oauth2_design_eval"
```

QA-oriented capabilities are defined the same way, for example `id: "qa.acceptance_validation"` (executing test cases and acceptance criteria against a produced artifact and recording a pass/fail test result) and `id: "qa.traceability_check"` (confirming every requirement in scope has covering, passing test cases). These are the capabilities used to select the QA agent described in section 13.5.

### 12.2 Matching algorithm

**Hard filters:**

- Agent is active and healthy.
- Required capability and minimum proficiency are present.
- Agent classification clearance is sufficient.
- Required tools are permitted.
- Model satisfies residency and policy.
- Agent is not excluded by SPOC or policy.
- Cost and token limits are feasible.

**Scoring factors:**

```text
score =
  0.35 * capability_coverage
+ 0.20 * evaluation_quality
+ 0.15 * relevant_project_context
+ 0.10 * tool_compatibility
+ 0.10 * model_fit
+ 0.05 * availability
+ 0.05 * cost_efficiency
- risk_penalties
```

Weights are configuration, not hard-coded policy. Selection evidence is stored in the run manifest.

### 12.3 Capability inference

An LLM may propose additional capabilities from the procedure. It returns structured candidates with confidence and quoted procedure evidence. The compiler then:

- Maps candidates to known capability IDs.
- Rejects nonexistent capabilities unless a human creates them.
- Adds low-risk inferred capabilities automatically only if policy permits.
- Requires human review for high-risk or access-expanding capabilities.
- Never removes explicit capabilities.

### 12.4 Multi-agent composition

Prefer the smallest team that covers all required capabilities. Use a primary agent plus delegate tools when tasks are tightly bounded. Use a Crew when specialists must contribute independently and outputs require synthesis. Avoid large crews by default because communication and verification cost rise quickly.

---

## 13. CrewAI runtime design

CrewAI concepts should map as follows:

| Platform concept | CrewAI construct | Responsibility |
|---|---|---|
| Project workflow | Flow | State, branching, routing, resume, approvals |
| Bounded collaboration | Crew | Coordinated specialist work |
| Work instruction | Task | One typed objective and expected output |
| Runtime specialist | Agent | Reasoning under scoped role and tools |
| Side-effect interface | Tool | Authorized external or repository action |
| Durable project state | Repository and database | Not agent memory alone |

### 13.1 Canonical project execution flow

```text
start
 -> load_run_manifest
 -> preflight_policy_check
 -> hydrate_typed_state
 -> create_execution_plan
 -> human_plan_approval_if_required
 -> execute_bounded_crews
 -> validate_outputs
 -> remediate_if_allowed
 -> qa_validation_against_test_cases
 -> [pass] specialist_review
 -> [fail] return_to_originating_agent -> execute_bounded_crews (bounded by retry_policy)
 -> human_acceptance_if_required
 -> stage_changes
 -> create_commit_or_pull_request
 -> finalize_run_summary
 -> update_project_indexes
 -> end
```

Every outcome produced by `execute_bounded_crews` passes through `qa_validation_against_test_cases` before it can proceed to human acceptance. This step is owned by a QA agent, not by the originating agent, and is detailed in section 13.5.

### 13.2 Typed state

```python
class ProjectRunState(BaseModel):
    run_id: str
    spoc_id: str
    manifest_hash: str
    status: str
    input_artifacts: list[ArtifactRef]
    selected_agents: list[ResolvedAgent]
    inferred_capabilities: list[CapabilityCandidate]
    decisions: list[DecisionRecord]
    produced_artifacts: list[ArtifactRef]
    validation_results: list[ValidationResult]
    approval_requests: list[ApprovalRequest]
    cost: CostState
    errors: list[RunError]
```

Do not place full confidential documents in state when references are sufficient.

### 13.3 Task design rules

Every task must have:

- One clear objective.
- Required context references.
- Expected structured output.
- Acceptance criteria.
- Tool allowlist.
- Resource limits.
- Failure behavior.
- Provenance requirements.

Task outputs should use Pydantic models when data is consumed by another automated step. Markdown is generated at the publication boundary.

### 13.4 Memory strategy

- **Working memory:** limited to the current task or crew.
- **Run memory:** typed flow state and run events.
- **Project memory:** approved OKF artifacts in the active project repository.
- **Global reusable memory:** curated content in the agent repository.
- **Private memory:** agent-specific restricted files with retention rules.

No unreviewed project content is promoted to global knowledge automatically.

### 13.5 QA gate and rework loop

Every SPOC outcome is checked by a QA agent before it can be accepted, using the same explicit-capability matching as any other work (section 12), typically requiring `qa.acceptance_validation`. The QA agent is a distinct actor from the agent that produced the outcome; a single agent never marks its own output as accepted.

1. The QA agent reads the SPOC's `output.acceptance_criteria` and the `test_case_refs` they point to (section 10.2), plus any test cases the requirement declares through `tested_by` (section 9.7).
2. It executes or evaluates each test case against the produced artifact and writes one `test_result` OKF file per test case (section 9.7), with `produces` linking back to the test case and `pass` or `fail` recorded in front matter.
3. If every required test case and acceptance criterion passes, the SPOC proceeds to `specialist_review` and, where required, `human_acceptance_if_required`.
4. If any required test case or acceptance criterion fails, the QA agent rejects the outcome. The SPOC transitions `review -> rejected -> ready` (section 10.3) and the task is returned to the **originating agent**, not to a generic queue, together with the failing test result references and the QA agent's stated reasons.
5. The originating agent reworks the output within the SPOC's `retry_policy.max_attempts` (section 10.2). Each rework attempt is a new run against the same SPOC, and re-enters `qa_validation_against_test_cases` before it can advance.
6. If `max_attempts` is exhausted with a failing result, the SPOC moves to `blocked` or `dead_letter` (section 10.3, section 19) and is escalated to a human rather than looping indefinitely.

Every step in this loop is logged: QA agent assignment, each test case execution, each test result, the rejection reason and target agent, and the resulting state transition are all mandatory run events (section 16.2), and the run summary (section 16.3) links to every test result produced during the run. This ensures the rework loop is fully auditable and that no outcome can reach acceptance without recorded, evidenced QA.

### 13.6 Conversational query flow for the Project Manager agent

The Project Manager agent (section 11.4) runs a separate, lightweight CrewAI Flow from the project execution flow in section 13.1. This query flow is stateless across turns except for its own session state, is read-only, and never triggers `execute_bounded_crews` or writes artifacts:

```text
start
 -> load_session_state
 -> authorize_query_scope
 -> query_graph_and_evidence
 -> compose_grounded_answer
 -> attach_citations
 -> log_chat_event
 -> end
```

Because it shares the same graph, indexes, and run evidence as the web UI (section 9.6 and 21, Phase 9), a user can ask the agent a question in the chat panel and then click through the citations it returns to open the underlying OKF files or run summaries directly in the graph view.

---

## 14. Tool architecture and MCP

### 14.1 Tool contract

Each tool has a registry definition with:

- Tool ID and version.
- Description and owner.
- Input and output schemas.
- Side-effect category.
- Required permissions.
- Network destinations.
- Data classifications.
- Timeout and retry policy.
- Idempotency behavior.
- Audit requirements.
- Test and security evidence.

### 14.2 Tool categories

- Read-only repository tools.
- Scoped write and patch tools.
- Git branch, commit, and pull-request tools.
- Schema and policy validators.
- Search and retrieval tools.
- Build and test tools.
- Ticketing and project-management connectors.
- Notification and approval tools.
- MCP adapters.

### 14.3 MCP policy

VS Code can expose MCP servers during development, but production execution should not depend on an interactive VS Code process. MCP server declarations are versioned, allowlisted, and separated by environment. The runtime connects only to approved servers and passes scoped credentials.

### 14.4 File-system protections

- Normalize and canonicalize every path.
- Reject paths outside mounted roots.
- Reject symbolic-link escapes.
- Separate read and write permissions.
- Prevent writes to policy and registry locations.
- Use atomic writes and file locks.
- Calculate before and after hashes.
- Scan staged content for secrets.
- Record every read and write event.

### 14.5 Git operating model

- One run uses one branch: `run/<spoc-id>/<run-id>`.
- Agents never push directly to protected branches.
- Commits are signed where infrastructure supports it.
- Commit message includes SPOC ID and run ID.
- Generated artifacts include provenance.
- Pull requests contain validation evidence and human approvals.
- Merge is controlled by repository rules, not the agent prompt.

---

## 15. Security, privacy, and governance

### 15.1 Trust boundaries

- Human interface to control plane.
- Control plane to execution worker.
- Worker to repositories.
- Worker to model provider.
- Worker to MCP or external systems.
- Public project space to private project space.
- Project knowledge to global reusable knowledge.

### 15.2 Identity

Every actor has a machine-readable identity:

- `human:<directory-id>`
- `agent:<agent-id>@<version>`
- `service:<service-id>`
- `tool:<tool-id>@<version>`

Agent identity is not equivalent to human identity. Human approvals use authenticated human identities.

### 15.3 Authorization

Use policy-based authorization with attributes including actor, project, classification, operation, path, tool, environment, and SPOC. Authorization is checked before every side effect, not only at run start.

### 15.4 Prompt injection controls

- Treat repository content and external content as untrusted data.
- Separate system instructions, policy, procedure, and retrieved content.
- Prevent retrieved text from changing tool permissions.
- Label sources and trust levels.
- Require confirmation for instructions found inside documents.
- Validate all tool arguments independently of the LLM.
- Scan output for attempted policy or secret exfiltration.

### 15.5 Secret management

- Store secrets only in an approved secrets manager.
- Provide short-lived credentials to tools.
- Never expose raw secrets to an agent if the tool can use them internally.
- Redact logs and traces.
- Rotate credentials after suspected leakage.

### 15.6 Data classification

Suggested levels:

- Public
- Internal
- Confidential
- Strictly confidential
- Regulated

Each model, agent, tool, storage target, and network route declares allowed classifications. The effective permission is the most restrictive intersection.

### 15.7 Human approval matrix

Human approval is mandatory for:

- Scope, budget, or baseline changes.
- Access expansion.
- Policy exceptions.
- High-risk inferred capabilities.
- External communication in the organization’s name.
- Production changes.
- Legal, regulatory, safety, employment, or financial conclusions.
- Promotion of private project knowledge to global knowledge.
- Activation of new agents or tools.

---

## 16. Audit, provenance, and observability

### 16.1 Event schema

```json
{
  "schema_version": "run-event/1.0",
  "event_id": "evt_...",
  "run_id": "run_...",
  "correlation_id": "corr_...",
  "parent_event_id": null,
  "timestamp": "2026-08-22T08:00:00Z",
  "event_type": "tool_call_completed",
  "actor": "agent:security_architect@1.3.0",
  "spoc_id": "SPOC-2026-0042",
  "tool": "repository.read@1.0.0",
  "input_refs": ["public/user_stories/US-001.md"],
  "output_refs": [],
  "decision_ref": null,
  "classification": "confidential",
  "duration_ms": 221,
  "cost": {"currency": "USD", "amount": 0.01},
  "result": "success",
  "error": null,
  "redaction_applied": true,
  "integrity_hash": "sha256:..."
}
```

### 16.2 Mandatory event types

- Run compiled, started, resumed, cancelled, completed, failed.
- State transition.
- Capability inferred and resolved.
- Agent selected or rejected.
- Model selected.
- Input read.
- Tool call requested, authorized, completed, or denied.
- Delegation requested and completed.
- Artifact created or changed.
- Validation passed or failed.
- Test case executed.
- Test result recorded, pass or fail.
- QA review passed or rejected, with target agent for rework.
- Decision proposed or approved.
- Human approval requested, granted, rejected, or expired.
- Budget threshold reached.
- Security event.

### 16.3 Run summary

Each run creates a human-readable `summary.md` containing:

- Objective and SPOC.
- Input versions and hashes.
- Selected agents, models, skills, and tools.
- Capability matching rationale.
- Material decisions and assumptions.
- Files read and changed.
- Validation results.
- Human interventions.
- Cost and token usage.
- Errors, retries, and unresolved risks.
- Links to raw events and outputs.

Each `summary.md` is itself an OKF file (section 9.5) with `relations` of type `generated_by` back to its SPOC or outcome and `evidenced_by` forward to its `events.jsonl`, so the graph and the web UI can navigate directly from an outcome to the log evidence of the run that produced it.

### 16.4 Metrics

**Reliability:** completion rate, retry rate, dead-letter rate, schema failure rate, tool failure rate.  
**Quality:** acceptance rate, defect escape rate, reviewer corrections, requirement coverage, grounded-claim rate.  
**Operations:** queue latency, execution duration, availability, resume success.  
**Economics:** cost per accepted SPOC, model cost, tool cost, rework cost.  
**Governance:** approval lead time, policy denials, access violations, stale knowledge, unowned artifacts.  
**Project value:** milestone predictability, blocked work age, risk closure, deliverable acceptance.

Do not use agent self-assessment as the only quality metric.

---

## 17. API and CLI design

### 17.1 Initial CLI

```text
mas project init --template <version>
mas project validate
mas spoc create --template standard
mas spoc validate <id>
mas spoc compile <id>
mas spoc execute <id>
mas run status <run-id>
mas run cancel <run-id>
mas run resume <run-id>
mas run evidence <run-id>
mas registry validate
mas agent scaffold <agent-id>
mas index rebuild
mas graph rebuild
mas chat
```

### 17.2 REST API

```text
POST   /api/v1/projects
GET    /api/v1/projects/{project_id}
POST   /api/v1/spocs/{spoc_id}/validate
POST   /api/v1/spocs/{spoc_id}/compile
POST   /api/v1/spocs/{spoc_id}/runs
GET    /api/v1/runs/{run_id}
POST   /api/v1/runs/{run_id}/cancel
POST   /api/v1/runs/{run_id}/resume
GET    /api/v1/runs/{run_id}/events
POST   /api/v1/approvals/{approval_id}/decision
GET    /api/v1/registry/agents
GET    /api/v1/registry/capabilities
GET    /api/v1/graph
GET    /api/v1/graph/nodes/{node_id}
GET    /api/v1/graph/nodes/{node_id}/neighbors
POST   /api/v1/chat/sessions
POST   /api/v1/chat/sessions/{session_id}/messages
GET    /api/v1/chat/sessions/{session_id}/stream
```

Use server-sent events for read-only run-stream updates initially. Use a queue or broker for worker dispatch in shared environments.

### 17.3 API requirements

- OAuth/OIDC authentication.
- OpenAPI specification.
- Idempotency keys for mutating calls.
- Optimistic concurrency for state changes.
- Pagination and filtering.
- Correlation IDs.
- Rate limits and quotas.
- No raw chain-of-thought exposure.
- Structured problem responses.

---

## 18. Operational state and concurrency

### 18.1 Database entities

- projects
- spocs
- compiled_manifests
- runs
- run_steps
- events
- leases
- approvals
- artifacts
- model_usage
- tool_calls
- policy_decisions
- registry_snapshots

### 18.2 Idempotency

A run request is uniquely identified by project ID, SPOC ID, SPOC version hash, and idempotency key. Repeating the same request returns the existing run unless the caller explicitly requests a new attempt.

### 18.3 Leases

Workers acquire time-limited leases. A heartbeat renews the lease. Expired leases can be recovered only after checking whether the previous worker produced side effects. Side-effecting tools must support idempotency or reconciliation.

### 18.4 Cancellation

Cancellation is cooperative. The flow checks cancellation between steps and tools receive cancellation tokens where supported. If a tool cannot cancel, the run enters `cancelling` until the call returns or times out.

---

## 19. Error handling and recovery

### 19.1 Error classes

- Validation error
- Authorization error
- Policy denial
- Missing capability
- Missing dependency
- Model error
- Transient tool error
- Permanent tool error
- Output schema error
- Quality gate failure
- Budget exceeded
- Human approval rejected or expired
- State conflict
- Security incident

### 19.2 Retry policy

- Retry only known transient failures.
- Use exponential backoff with jitter.
- Do not repeat irreversible tool calls without an idempotency key.
- Schema remediation is a separate bounded attempt.
- Quality rejection returns to a defined prior state.
- Exhausted runs move to dead letter with evidence.

### 19.3 Recovery

- Resume from persisted flow state.
- Revalidate hashes of inputs before resuming.
- Detect changed dependencies and require recompilation.
- Reconcile Git branches and tool side effects.
- Never silently continue after security or authorization errors.

---

## 20. Testing and evaluation strategy

### 20.1 Test pyramid

1. Schema and pure-function unit tests.
2. Tool contract tests.
3. Repository adapter integration tests.
4. Flow transition tests.
5. Security and authorization tests.
6. Golden-scenario agent evaluations.
7. Failure injection and resilience tests.
8. End-to-end project simulations.

### 20.2 Required test scenarios

- Valid and invalid OKF files.
- SPOC with missing input.
- Conflicting capability aliases.
- No eligible agent.
- Multiple eligible agents with deterministic tie-break.
- High-risk inferred capability.
- Private file access denied.
- Symbolic-link path escape.
- Prompt injection in a requirement document.
- Tool timeout and retry.
- Duplicate execution request.
- Worker loss and resume.
- Budget exceeded.
- Human approval rejected.
- Output schema invalid.
- Git merge conflict.
- New agent activation blocked without evaluations.
- User story missing a linked test case.
- QA rejection returns the SPOC to the originating agent and a subsequent attempt passes.
- QA rejection exhausts `retry_policy.max_attempts` and escalates to a human.
- Requirement whose most recent linked test result is a fail is reported as not currently passing.

### 20.3 Agent evaluations

Each claimed capability has a versioned evaluation dataset with:

- Input fixture.
- Expected structured properties.
- Required and prohibited behaviors.
- Deterministic validators.
- Human rubric where needed.
- Baseline result.
- Model and prompt version.
- Regression threshold.

### 20.4 Release gates

A release must pass:

- Static analysis and formatting.
- Unit and integration tests.
- Schema compatibility tests.
- Security tests and dependency scan.
- Agent evaluation regression suite.
- Migration test from previous supported version.
- Container build and software bill of materials generation.
- Disaster-recovery rehearsal for production releases.

---

## 21. Delivery roadmap

### Phase 0: Decisions and foundations

**Objectives**

- Confirm scope, risk classification, deployment model, and supported project type.
- Create architecture decision records.
- Establish repository ownership and branch protection.

**Deliverables**

- Project charter.
- Threat model.
- ADR set.
- Initial schemas.
- Definition of done.
- Evaluation baseline.

**Exit criteria**

- G0 and G1 approved.
- Trust boundaries and human approval matrix agreed.

### Phase 1: Repository bootstrap and schema toolchain

**Build**

- Three repositories and template release process.
- OKF and SPOC schemas.
- Validator, linter, index generator, and migration skeleton.
- CLI commands for init and validate.

**Exit criteria**

- A project can be generated from a pinned template.
- CI rejects invalid artifacts and broken references.

### Phase 2: Registry, capability catalog, and deterministic matcher

**Build**

- Agent, capability, skill, tool, model, and workflow registries.
- Hard-filter matcher and explainable scoring.
- Registry validators and health status.
- Agent scaffolding workflow.

**Exit criteria**

- Matching is deterministic for explicit capabilities.
- Every selection and rejection has machine-readable reasons.

### Phase 3: CrewAI flow runtime

**Build**

- Typed run state.
- Canonical ProjectExecutionFlow.
- Crew and task factories.
- Structured outputs.
- Controlled delegate tool.
- Local SQLite state and event logging.

**Exit criteria**

- One bounded SPOC can execute end-to-end locally.
- Run can resume after intentional interruption.

### Phase 4: Secure repository and Git tools

**Build**

- Scoped read/write tools.
- Path security controls.
- Branch-per-run workflow.
- Secret scanning and checksum manifests.
- Pull-request evidence generation.

**Exit criteria**

- No worker can write outside the manifest allowlist.
- All file mutations are attributable and reversible.

### Phase 5: Policy, approvals, budgets, and model routing

**Build**

- Policy engine.
- Human approval states and API.
- Model profiles and routing constraints.
- Token, cost, runtime, and delegation limits.
- Capability inference with governance.

**Exit criteria**

- High-risk operations cannot proceed without authenticated approval.
- Budget exhaustion stops safely.

### Phase 6: API, worker isolation, and shared deployment

**Build**

- FastAPI control-plane service.
- PostgreSQL operational state.
- Queue-backed workers.
- Container isolation.
- SSE event stream.
- OIDC and role-based access.

**Exit criteria**

- Multiple projects can run without state leakage.
- Worker loss and lease recovery pass tests.

### Phase 7: Project-management workflows

**Build**

- Intake, planning, change, risk, status, acceptance, and closure flows.
- RAID and decision-log management.
- Milestone and dependency tracking.
- Evidence-grounded status reporting.

**Exit criteria**

- A reference project can progress through all stage gates.
- Status reports trace every claim to project evidence.

### Phase 8: Observability, evaluation, and production hardening

**Build**

- Metrics, traces, dashboards, alerts.
- Regression evaluation suites.
- Failure injection.
- Backup, restore, retention, and incident runbooks.
- Performance and cost optimization.

**Exit criteria**

- Agreed reliability and quality thresholds are met.
- Security review and operational readiness review approved.

### Phase 9: Web interface

**Build**

- Project overview.
- SPOC editor with schema validation.
- Run timeline and evidence viewer.
- Approval inbox.
- Agent and capability registry views.
- Cost and quality dashboards.
- Interactive knowledge graph view, with nodes and edges rendered from the generated graph index (section 9.6), colored and iconified by OKF `type`, with a visible legend.
- Document viewer that renders an OKF file's content plus its `relations`, `source_refs`, and `cross_references` as clickable links, including backlinks (artifacts that reference the current one).
- Deep links resolved by stable OKF `id` rather than file path, so links survive files moving or being renamed.
- "Jump to evidence" action on any outcome, deliverable, or decision node that opens the run summary and, from there, the underlying `events.jsonl` for the run that produced it.
- Search and filter by type, tag, status, owner, and classification.
- A persistent "Ask the Project Manager" chat panel, available from every screen, backed by the chat API (section 17.2) and the query flow (section 13.6), with citations rendered as links into the graph and document viewer.

**Exit criteria**

- UI is a client of the same API and does not bypass policy.
- A user can navigate from any project outcome to its SPOC, its run summary, and its raw log evidence using only graph and document-viewer links.
- The Project Manager chat panel is reachable from every screen and every answer links back to the graph nodes it cites.

---

## 22. Suggested initial product backlog

### Epic A: File and schema foundation

- Define OKF 1.1 JSON Schema.
- Define SPOC 1.1 JSON Schema.
- Define epic, user story, test case, and test result schemas.
- Implement canonical hashing.
- Implement cross-reference validator.
- Implement generated directory indexes.
- Add template lock and migration metadata.

### Epic B: Registry

- Define agent schema.
- Define capability ontology.
- Define tool and model schemas.
- Build registry loader and validator.
- Build deterministic matcher.
- Add matching explanation report.

### Epic C: Runtime

- Implement run compiler.
- Implement typed state.
- Implement canonical CrewAI Flow.
- Create Crew and Task factories.
- Implement bounded delegation.
- Implement cancellation and resume.

### Epic D: Security and governance

- Implement path allowlists.
- Implement policy checks.
- Integrate secret manager abstraction.
- Add prompt injection test corpus.
- Add human approvals.
- Add signed run manifests.

### Epic E: Evidence and operations

- Implement JSONL event writer.
- Generate Markdown run summary.
- Add cost and token accounting.
- Add metrics and traces.
- Build dead-letter and reconciliation commands.

### Epic F: Project workflows

- Build project intake flow.
- Build planning and baseline flow.
- Build requirement-to-delivery flow.
- Build change-control flow.
- Build risk escalation flow.
- Build closure and learning flow.

### Epic G: Knowledge graph and conversational interface

- Implement the graph generator that derives nodes and edges from OKF front matter and relations (section 9.6).
- Define the type-to-visual-style mapping and legend as configuration, not hard-coded UI logic.
- Implement graph and chat REST endpoints (section 17.2).
- Implement the Project Manager agent's read-only tools and query flow (sections 11.4 and 13.5).
- Build the graph view, document viewer with clickable relations and backlinks, and the persistent chat panel in the web UI.
- Add regression tests that every generated `summary.md` links back to its SPOC and forward to its raw events, and that the graph contains no orphaned or dangling relations.

### Epic H: Requirements traceability and QA rework loop

- Implement epic, user story, test case, and test result OKF templates and schemas.
- Implement CI checks for `part_of` and `tested_by` coverage, flagging untested user stories.
- Implement the QA agent role, its read/execute tool allowlist, and `qa.acceptance_validation` / `qa.traceability_check` capabilities.
- Implement the `qa_validation_against_test_cases` flow step and the `return_to_originating_agent` rework path bounded by `retry_policy`.
- Implement test-result generation, including `produces`, `evidenced_by`, and `generated_by` relations back to the test case and run summary.
- Add regression tests for the full rework loop: rejection, bounded retries, and escalation to a human on exhaustion.

---

## 23. Definition of done for one SPOC

A SPOC is done only when:

- Schema and references are valid.
- Inputs and versions are fixed in a run manifest.
- Agent, model, skill, and tool selections are recorded.
- Policy and access checks passed.
- Required outputs exist at approved locations.
- Outputs pass schemas and quality gates.
- Requirement traceability is complete.
- Every acceptance criterion's linked test case has been executed by the QA agent and produced a passing test result.
- Material decisions and assumptions are recorded.
- Human approvals are present where required.
- Run events and summary are complete.
- Git changes are reviewed and merged or explicitly rejected.
- Follow-up risks, issues, and actions have owners.
- Cost and resource usage are recorded.
- The SPOC is in a terminal state.

---

## 24. Key architecture decisions to record

- ADR-001: Use CrewAI Flows for orchestration and Crews for bounded collaboration.
- ADR-002: Use Git and OKF as authoritative project records.
- ADR-003: Use an operational database for concurrency and resumability.
- ADR-004: Separate control plane and execution plane.
- ADR-005: Use deterministic capability matching with governed semantic inference.
- ADR-006: Enforce branch-per-run and protected main branches.
- ADR-007: Use policy-enforced tools rather than relying on prompt restrictions.
- ADR-008: Keep global and project knowledge separate.
- ADR-009: Require human approval for consequential actions.
- ADR-010: Version all registries, schemas, prompts, workflows, and evaluations.

---

## 25. Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Agents produce plausible but unsupported output | Bad project decisions | Provenance, source references, deterministic validation, human review |
| Recursive delegation | Runaway cost and unclear accountability | Depth, call, cost, and time limits |
| Private data leakage | Security or compliance incident | Classification labels, scoped mounts, policy engine, redaction |
| Git merge conflicts | Lost or delayed work | Branch-per-run, atomic artifacts, generated indexes |
| Framework version change | Runtime breakage | Dependency pinning, adapter layer, regression suite |
| Capability inflation | Wrong agent selection | Evidence-backed capabilities and minimum proficiency |
| Prompt injection | Unauthorized actions | Tool-side authorization and untrusted-content handling |
| Markdown concurrency | Corrupted state | Operational database and per-run event files |
| Silent model changes | Quality regression | Model catalog, pinned profiles, eval gates |
| Excess autonomy | Consequential errors | Stage gates and explicit approval matrix |
| Knowledge contamination | Reuse of incorrect or confidential content | Curated promotion workflow |
| Cost unpredictability | Budget overruns | Per-run budgets and model routing |

---

## 26. Recommended technology baseline

This is a starting recommendation and should be captured in ADRs before implementation.

- Python 3.12 or the CrewAI-supported version selected by the team.
- CrewAI pinned through `uv.lock`.
- Pydantic for typed contracts.
- FastAPI for control-plane API.
- Typer for CLI.
- SQLite locally and PostgreSQL for shared deployment.
- JSON Schema for file-level validation.
- OpenTelemetry for traces and metrics.
- Structured JSON logging plus JSONL evidence.
- Pytest, Ruff, mypy or Pyright, Bandit, and dependency scanning.
- Docker or equivalent container build.
- GitHub, GitLab, or Azure DevOps with protected branches.
- A provider-neutral model adapter and explicit model catalog.
- MCP only through a governed adapter layer.

---

## 27. First vertical slice

The first vertical slice should prove the control model rather than maximum intelligence.

**Scenario:** Convert one approved user story into a reviewed architecture note and requirement traceability matrix.

**Agents:**

- Project planner.
- Domain architect.
- Quality reviewer.

**Flow:**

1. Validate user story and SPOC.
2. Compile manifest.
3. Match agents using explicit capabilities.
4. Request approval for the execution plan.
5. Generate typed architecture content.
6. Validate sources, schema, and traceability.
7. Run independent quality review.
8. Write outputs to run branch.
9. Generate run evidence.
10. Request acceptance and open pull request.

**Success criteria:**

- No unrestricted file access.
- Deterministic rerun from the same manifest.
- Resume after interruption.
- Complete parent-child audit trail.
- Invalid or unsupported claims are rejected.
- Cost limit is enforced.
- Human can reject and return the SPOC for rework.

---

## 28. Implementation guidance for the coding agent

1. Create ADRs before building major components.
2. Build schemas and validators before LLM prompts.
3. Implement interfaces around CrewAI to reduce framework coupling.
4. Keep tools small, typed, and independently testable.
5. Treat every LLM output as untrusted until validated.
6. Use fixtures and fake model adapters in most tests.
7. Do not implement the web UI before the CLI vertical slice passes.
8. Do not let the execution worker read the complete agent repository.
9. Do not store chain-of-thought. Store concise decision records and evidence.
10. Do not promote private knowledge automatically.
11. Do not invent capabilities at runtime.
12. Do not use one shared mutable Markdown audit file.
13. Pin dependencies and record the CrewAI version in each run manifest.
14. Add compatibility tests before upgrading CrewAI.
15. Make all generated artifacts editable and understandable by humans.

---

## 29. Acceptance criteria for the platform MVP

- A project can be initialized from a pinned template.
- Invalid OKF and SPOC files are blocked by CLI and CI.
- The matcher selects eligible agents deterministically and explains why.
- One CrewAI Flow executes a SPOC end-to-end.
- A run can pause for human approval and resume.
- A cancelled or interrupted run does not silently continue.
- Agents can only read and write manifest-approved paths.
- Every tool call produces a structured event.
- Output schemas and acceptance criteria are evaluated.
- All changes occur on a run-specific Git branch.
- Costs, tokens, models, prompts, tools, and agent versions are traceable.
- The system detects duplicate execution requests.
- Private artifacts are not available to unauthorized agents.
- A failed run can be diagnosed from evidence without exposing secrets.
- A new agent cannot become active without tests and approval.
- Every user story is clustered under an epic and has at least one linked test case, and CI flags any that are not.
- Every SPOC outcome is validated by a QA agent against its acceptance criteria and linked test cases before it can be accepted, and a failing result returns the SPOC to the originating agent for rework rather than to a generic queue.
- Every QA execution, test result, rejection reason, and rework attempt is recorded as a logged, auditable event and linked into the run summary.
- The generated knowledge graph has no dangling relations, and every outcome, decision, and deliverable can be traced through the graph to the run summary and log evidence that produced it.
- The Project Manager agent answers project-state questions at any time, grounded only in the graph and evidence, with citations, and declines to answer when evidence is insufficient rather than fabricating a response.

---

## 30. Open decisions for project inception

These decisions should be documented, not left implicit:

- Which project types are supported first?
- Which actions require human approval in the first deployment?
- Which data classifications may be sent to which model providers?
- Is the system local-only, on-premises, cloud-hosted, or hybrid?
- Which Git platform is authoritative?
- Which identity provider and secrets manager are used?
- Which project-management system, if any, is synchronized?
- What is the maximum allowed delegation depth and run budget?
- Which quality metrics are release gates?
- Which artifacts must remain Markdown and which can be external binaries?
- What retention rules apply to prompts, outputs, events, and private workspaces?
- Who owns each agent, capability, tool, workflow, and policy?

---

## 31. Source notes

The source requirements were taken from `prompt.md`. The earlier `architecture_plan.md` was used as a concept draft and revised substantially. CrewAI's current documentation describes agents, tasks, crews, flows, state handling, structured outputs, guardrails, memory, knowledge, and observability. This plan deliberately uses Flows for project orchestration and Crews for bounded collaborative execution so that project control remains explicit.

---

## 32. Final recommendation

Start with a narrow, governed vertical slice and deliberately postpone dynamic agent creation, broad MCP connectivity, and autonomous project replanning until the platform can demonstrate safe file access, deterministic routing, resumability, structured evidence, and reliable quality gates. The durable asset is not the collection of prompts. It is the combination of versioned contracts, reusable capability definitions, controlled tools, project knowledge, evaluations, and auditable execution.
