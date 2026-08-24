# Threat model

Plan milestone M0.3. Covers the trust boundaries in masterplan section
15.1, the actors in section 5.1, and the prompt-injection /
secret-exfiltration risks in sections 15.4-15.5. Every trust boundary
below lists at least one threat and at least one mitigating control mapped
to a later milestone.

## Scope and method

Threats are described in a lightweight table form rather than a full STRIDE
decomposition; the MVP threat landscape is small (single operator, local
first) and the goal is to anchor each control to a milestone rather than
to exhaustively enumerate the model landscape. A full STRIDE pass is a
follow-up once the shared-deployment topology (Phase 6) is designed.

## Trust boundaries

### 1. Human interface to control plane

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T1 | Untrusted project content reaches the matcher/compiler and expands agent scope | Capability matching is deterministic; inferred high-risk capabilities require human approval | M2.3, M2.4 |
| T2 | Malformed SPOC/OKF accepted as valid | JSON Schema + OKF linter + xref validator fail closed | M1.2-M1.5 |
| T3 | Operator action not attributable | `IdentityContext` records `human:<id>` actor on every decision/event | M6.1 |

### 2. Control plane to execution worker

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T4 | Worker receives more than its manifest allows | Only the immutable compiled `RunManifest` is handed to the worker; no mutable SPOC | M3.2 |
| T5 | Worker mutates registry/policy | Execution plane has no write path to registry or policy (ADR-004) | M3.3 |
| T6 | Missing/forged approval before a consequential step | Durable `ApprovalGateway` with `waiting_for_human` state | M5.2, M3.3 |

### 3. Worker to repositories

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T7 | Path traversal / symlink escape out of mounted roots | Path security kernel: canonicalize, reject escapes, allowlists | M4.1 |
| T8 | Write to policy/registry or protected branches | Scoped write allowlist + branch-per-run + protected main | M4.1, M4.2, M4.3 |
| T9 | Secret committed to repository | Secret scanning before staging; scoped tools | M4.2, M5.4 |

### 4. Worker to model provider

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T10 | Confidential data sent to an ineligible provider | `confidential_eligible` flag + classification × provider matrix | M5.3 |
| T11 | Model fallback broadens data access | Fallback policy forbids broadening access | M5.3 |
| T12 | Silent model/prompt change alters behavior | Execution fingerprint records model/prompt hashes | M3.2, M5.3 |

### 5. Worker to MCP or external systems

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T13 | Unapproved MCP server connected | MCP allowlist, versioned, environment-separated | M4.4 |
| T14 | External content drives unauthorized tool use | Tool arguments validated independently of the LLM | M4.2 |

### 6. Public project space to private project space

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T15 | Cross-project/classification data bleed | Per-agent classification limits + scoped mounts | M4.1, M5.1 |
| T16 | Agent reads a private file it should not | Read permission enforced per manifest allowlist, not per prompt | M4.1 |

### 7. Project knowledge to global reusable knowledge

| # | Threat | Mitigation | Milestone |
|---|---|---|---|
| T17 | Project-confidential content promoted to global knowledge automatically | No automatic promotion; curated, human-reviewed workflow | W7/W8 backlog |

## Prompt injection (masterplan 15.4)

Prompt injection is the highest-leverage runtime threat because an LLM is
used to interpret untrusted repository/external content. Controls, in
priority order:

1. Tool-side authorization independent of the LLM (ADR-007) — M4.1/M4.2.
2. Retrieved/system/procedure content kept separate from user content; no
   retrieved text can change tool permissions — M4.2.
3. Validation of every tool argument without trusting the model — M4.2.
4. Output scanning for attempted secret exfiltration — M5.4.

## Secret management (masterplan 15.5)

The MVP (local-first, single operator) uses `.env`-based secrets per
`DEC-INCEPTION-001`. Risks and residual controls:

- **R1:** secrets in logs/traces → redaction at the event-projection
  boundary (`RunEvent.payload` must be pre-redacted) — M3.7 + M5.4.
- **R2:** secrets committed to Git → pre-commit scan hook — M4.2.
- **R3:** no rotation → documented rotation runbook — M8.1 operations.

## Residual risk register

| ID | Risk | Owner | Status |
|---|---|---|---|
| R1 | `.env` secrets have no managed rotation for MVP | project_architect | accepted for MVP; ADR before Phase 6 multi-user |
| R2 | No real sandbox for `ToolExecutor` yet (FakeToolExecutor in tests) | platform_engineering | open; ADR-020 follow-up |
| R3 | `ProjectExecutionFlow` not yet a `crewai.Flow` subclass | platform_engineering | open; documented deviation |
