# agent-repository documentation index

This is the navigation root for `agent-repository`'s documentation, per
`plan/implementation_plan_enhanced_v1.1.md` section 17 (documentation-as-code
strategy). This file is currently maintained by hand; a `mas docs` generator
(plan section 17.8) will later regenerate it and add a coverage report.

## Categories

- [`architecture/`](architecture/) — context, container, component, and
  trust-boundary views.
- [`decisions/`](decisions/) — ADR-001 through ADR-022 (masterplan section
  24; plan section 18). Project inception decisions live at
  [`/plan/decisions/inception_decisions.md`](../../plan/decisions/inception_decisions.md)
  at the workspace root.
- [`implementation/`](implementation/) — mirrored module and class
  documentation for `src/agent_platform/`.
- `api/` — not yet applicable (no HTTP API implemented yet, Phase 6).
- `cli/` — not yet applicable as a separate category; CLI commands are
  documented alongside their implementation module
  ([`implementation/agent_platform/cli/`](implementation/agent_platform/cli/module.md)).
- `configuration/` — not yet applicable (no environment configuration
  surface implemented yet).
- `security/` — see [`agent-repository/docs/security/threat_model.md`](security/threat_model.md)
  once M0.3 is executed; not yet written.
- `operations/` — not yet applicable (no deployment/runbook surface yet).
- [`testing/`](testing/) — test strategy summary.
- `generated/` — reserved for reproducible projections (none yet).
- [`glossary.md`](glossary.md) — controlled platform vocabulary.

## Current implementation coverage

| Package | Module doc | Notes |
|---|---|---|
| `agent_platform.schemas` | [module.md](implementation/agent_platform/schemas/module.md) | Phase 1: canonicalization, OKF linter, xref validator, index generator |
| `agent_platform.registries` | [module.md](implementation/agent_platform/registries/module.md) | Phase 2: agent/capability/skill/tool/model/workflow registries |
| `agent_platform.control_plane` | [module.md](implementation/agent_platform/control_plane/module.md) + [CompileSpocService.md](implementation/agent_platform/control_plane/CompileSpocService.md) | Phase 2/3: capability matcher, inference, explainer; Phase 3: SPOC compiler |
| `agent_platform.cli` | [module.md](implementation/agent_platform/cli/module.md) | `mas` CLI commands |
| `agent_platform.domain` | [module.md](implementation/agent_platform/domain/module.md) | Phase 3: typed run/project/event domain models |
| `agent_platform.application.ports` | [module.md](implementation/agent_platform/application/ports/module.md) | Phase 3: application ports (plan section 20.1) |
| `agent_platform.adapters` | [module.md](implementation/agent_platform/adapters/module.md) | Phase 3: in-memory/local test-double adapters behind the ports above |
| `agent_platform.execution_plane` | [module.md](implementation/agent_platform/execution_plane/module.md) + [ProjectExecutionFlow.md](implementation/agent_platform/execution_plane/ProjectExecutionFlow.md) | Phase 3: `ProjectExecutionFlow`, QA gate |
| `agent_platform.telemetry` | [module.md](implementation/agent_platform/telemetry/module.md) | Phase 3: event JSONL projection, run summary generation |

100% documentation coverage for required code units is a protected-branch
requirement (plan section 17.8) once CI enforces it; it is not yet enforced
by tooling (`mas docs validate` from plan section 17.8 is not implemented).
This table is the interim, hand-maintained substitute.
