
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
doc_id: CODE-DOC-COMPILE-SPOC-001
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
test_case_id: TC-RUNSTATE-RESUME-001
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
test_result_id: TR-001-TC-RUNSTATE-RESUME-001
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
3. Stable-ID and relationship validation
4. Documentation completeness and link checks
5. Architecture tests
6. Unit tests
7. Contract tests
8. Change-appropriate integration tests
9. Security static checks and secret scan
10. Generated documentation and traceability rebuild
11. Test evidence and result generation
12. Generated-file diff check
13. Quality-gate evaluation

Full evaluations, resilience, performance, and end-to-end suites may use controlled pipelines, but release test plans state which suites are mandatory.

---

## 19. Development Documentation and Test Engineering Agent

### 19.1 Purpose and timing

A governed development agent shall be specified at project inception and activated as soon as the minimum registry, tool permissions, and evaluation harness exist. Recommended ID:

```text
development_documentation_test_agent
```

It helps implement code, mirrored Markdown documentation, test-case documentation, deterministic test scaffolds, evidence, and traceability. It is invoked per implementation SPOC or pull-request task and is not a permanently running conversational context.

### 19.2 Required capabilities

```yaml
capabilities:
  - development.python.design
  - development.crewai.integration
  - development.documentation_as_code
  - development.api_documentation
  - testing.test_design
  - testing.pytest.scaffolding
  - testing.contract_testing
  - testing.traceability
  - testing.evidence_documentation
  - architecture.dependency_analysis
  - security.secure_coding_review
  - repository.git_change_preparation
```

Every claimed capability requires evaluation evidence. Secure-coding review does not authorize the agent to approve security exceptions.

### 19.3 Responsibilities

The agent may discover code units through approved AST tools; scaffold module/class Markdown; document purpose, contracts, invariants, dependencies, failure behavior, security, and observability; create test-case Markdown from requirements; scaffold deterministic tests and fixtures; add test IDs; run approved validators and tests; collect generated evidence; interpret failures; propose remediation; maintain traceability; and prepare a pull-request summary.

### 19.4 Prohibitions

The agent must not self-activate, self-approve, alter its own permissions, approve architecture/security/release gates, change expected test results to match observed behavior, delete failed evidence, weaken quality thresholds, add blanket ignores, quarantine tests without an exception, claim tests passed without executing deterministic tools, edit generated result Markdown, use unrestricted production data, expose secrets or hidden reasoning, or merge protected branches.

### 19.5 Agent files

```text
agent-repository/registry/agents/development_documentation_test_agent/
├── agent.yaml
├── prompt.md
├── private_knowledge/
│   ├── coding_standards.md
│   ├── documentation_standard.md
│   ├── test_strategy.md
│   └── secure_development_rules.md
├── tests/
│   ├── documentation_scaffold_eval.yaml
│   ├── test_case_design_eval.yaml
│   ├── traceability_eval.yaml
│   ├── no_result_fabrication_eval.yaml
│   ├── no_test_weakening_eval.yaml
│   └── security_boundary_eval.yaml
└── README.md
```

Where possible, private knowledge references approved source documentation instead of copying it.

### 19.6 Working flow

```text
Approved implementation SPOC
 -> load requirements, ADRs, documentation and test contracts
 -> create change-impact map
 -> implement or scaffold code
 -> create/update mirrored Markdown
 -> create/update test-case documents
 -> create/update deterministic tests
 -> run documentation validators
 -> execute permitted tests
 -> capture immutable evidence
 -> report failures without changing expectations
 -> propose remediation
 -> rerun as a new test execution
 -> update traceability and PR summary
 -> request independent review
```

### 19.7 Activation evaluations

The agent must demonstrate that it can add a public class and corresponding Markdown, preserve stable documentation identity through a refactor, create a test case and executable mapping from an acceptance criterion, report failure without manipulating expectations, refuse removal of a security test to make CI pass, detect missing traceability, separate deterministic from qualitative review, avoid secrets and hidden reasoning, prepare a complete PR summary, and leave approval to an independent authorized actor.

---

## 20. Additional milestones for documentation and testing

### M0.6 — Documentation and test governance baseline

**Deliverables**

- `docs/documentation_standard.md`
- `docs/testing/strategy/test_strategy.md`
- `docs/testing/strategy/test_documentation_standard.md`
- `docs/testing/strategy/release_quality_gates.md`
- Schemas `code-doc/1.0`, `test-case/1.1`, `test-result/1.1`, `test-run/1.0`, `defect/1.0`, and `test-fixture/1.0`
- ADR for Markdown tooling
- ADR for test evidence authority and retention

**Definition of done**

- Standards define mandatory documents, stable IDs, review, ownership, retention, and CI rules.
- Valid and invalid fixtures exist for each schema.
- The platform Definition of Done treats code, documentation, tests, and traceability as one deliverable.

### M0.7 — Development Documentation and Test Engineering Agent specification

**Deliverables**

- Agent definition, prompt, approved knowledge references, capability requirements, tools, and evaluation cases described in section 19

**Definition of done**

- The agent can be instantiated after registry and evaluation infrastructure exists.
- Prohibition tests cover result fabrication, test weakening, self-approval, and path escape.

### M1.10 — Mirrored documentation tree and validator

**Deliverables**

- `docs/implementation/` mirrored skeleton
- AST-based code-unit discovery
- `mas docs scaffold`, `validate`, `coverage`, `build`, and `link-check`
- Generated code/document index

**Definition of done**

- Missing and orphaned documentation are found deterministically.
- A module with two classes maps to `module.md` plus two class files.
- Required code-unit documentation coverage is calculated correctly.

### M1.11 — Test catalog and traceability generator

**Deliverables**

- `docs/testing/` tree
- Pytest test-case marker/plugin
- Test-case and test-result renderers
- Requirements/code/risks/workflows traceability projections

**Definition of done**

- Undocumented collected tests fail CI unless covered by a documented family rule.
- Manual tests are supported.
- Generated traceability rebuilds without diff.

### M2.6 — Activate the development documentation/test agent

**Dependencies**

- M0.7 complete
- Minimum agent/capability/tool registries complete
- Evaluation harness complete

**Definition of done**

- Activation scenarios pass their configured thresholds.
- Independent reviewer approves activation.
- Agent permissions are scoped to the compiled implementation SPOC.

### M3.10 — Test evidence pipeline

**Deliverables**

- Deterministic TestExecutor adapters
- Test-run manifest
- JUnit/log/coverage evidence ingestion
- Generated Markdown results and summaries
- Evidence hashing and immutable storage

**Definition of done**

- Passed, failed, blocked, skipped, and inconclusive outcomes are represented distinctly.
- Reruns preserve earlier results.
- Result Markdown is reproducible from raw evidence and manifest.

### M3.11 — Documentation-change enforcement

**Deliverables**

- Change-impact detector
- PR check requiring documentation and test-impact updates
- Governed exemption workflow

**Definition of done**

- Public-contract changes without matching documentation and test updates fail CI.
- Formatting-only changes do not cause false mandatory updates.
- Exemptions are scoped, owned, reasoned, and expiring.

### M8.6 — Documentation and test audit rehearsal

**Deliverables**

- Audit navigator from project goal to release evidence and back
- Audit findings and remediation records

**Definition of done**

- Representative requirements, code units, tests, results, approvals, and release evidence are navigable by stable ID.
- No missing mandatory class or test-case documentation remains.
- Reproducible tests can be rerun from documented configuration; non-deterministic evaluations follow their documented repeated-run and evidence policy.

### 20.1 Revised early sequence

```text
M0.1  Inception decisions
M0.2  ADRs
M0.3  Threat model
M0.4  Repository governance
M0.5  Definition of done and baseline
M0.6  Documentation and test governance baseline
M0.7  Development agent specification
M1.x  Repository, schemas, documentation tooling, and test catalog
M2.x  Registries and evaluation harness
M2.6  Activate development documentation/test agent
M3.x  Runtime plus deterministic evidence pipeline
```

The agent is designed early but activated only after registry controls, scoped tools, evaluations, and independent approval exist. Until activation, deterministic scaffolding tools and human review enforce the same standards.

### 20.2 Updated platform Definition of Done

A change is complete only when:

- Code and schemas are complete.
- Corresponding mirrored Markdown exists and validates.
- ADR and architecture impacts are addressed.
- Test-case documents exist for changed behavior.
- Deterministic tests execute and produce immutable evidence.
- Agent evaluations, when required, follow their documented repeated-run policy.
- Traceability projections are current.
- Security, failure, observability, and operational behavior are documented.
- Documentation and evidence contain no prohibited secrets or hidden reasoning.
- Review and approvals satisfy ownership and segregation-of-duties rules.
- Generated documentation, test summaries, and indexes rebuild without difference.
