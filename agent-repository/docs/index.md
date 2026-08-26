# agent-repository documentation index

This is the navigation root for `agent-repository`'s documentation, per
`plan/implementation_plan_enhanced_v1.1.md` section 17 (documentation-as-code
strategy). `mas docs validate` and `mas docs coverage` (section 17.8)
check the code-to-document mapping and report coverage.

> **New here?** Start with the [Project Manager Handbook](pm_handbook.md).

## Categories

- [Project Manager Handbook](pm_handbook.md) — quick start, creating
  projects, adding agents, OKF layout, stage gates, SPOCs, QA, and the
  web UI.
- [`architecture/`](architecture/) — context, container, component, and
  trust-boundary views.
- [`decisions/`](decisions/) — ADR-001 through ADR-022 (masterplan section
  24; plan section 18). Project inception decisions live at
  [`/plan/decisions/inception_decisions.md`](../../plan/decisions/inception_decisions.md)
  at the workspace root.
- [`implementation/`](implementation/) — mirrored module and class
  documentation for `src/agent_platform/`.
- [`api/`](api/openapi.json) — the committed OpenAPI spec for the FastAPI
  control plane (Phase 6, M6.1); implementation doc at
  [`implementation/agent_platform/api/module.md`](implementation/agent_platform/api/module.md).
- `cli/` — not yet applicable as a separate category; CLI commands are
  documented alongside their implementation module
  ([`implementation/agent_platform/cli/`](implementation/agent_platform/cli/module.md)).
- `configuration/` — not yet applicable (no environment configuration
  surface implemented yet).
- `security/` — see [`agent-repository/docs/security/threat_model.md`](security/threat_model.md)
  (M0.3 threat model).
- [`operations/`](operations/backup_restore.md) — backup/restore, retention
  policy, incident runbook, and the performance/cost report (Phase 8,
  M8.4-M8.5).
- [`web/`](../web/README.md) — the dependency-free static web UI (Phase 9,
  M9.4-M9.6; ADR-023).
- [`testing/`](testing/) — test strategy summary.
- `generated/` — reserved for reproducible projections (none yet).
- [`glossary.md`](glossary.md) — controlled platform vocabulary.

## Current implementation coverage

| Package | Module doc | Notes |
|---|---|---|
| `agent_platform.schemas` | [module.md](implementation/agent_platform/schemas/module.md) | Phase 1: canonicalization, OKF linter, xref validator, index generator |
| `agent_platform.registries` | [module.md](implementation/agent_platform/registries/module.md) | Phase 2: agent/capability/skill/tool/model/workflow registries |
| `agent_platform.control_plane` | [module.md](implementation/agent_platform/control_plane/module.md) + [CompileSpocService.md](implementation/agent_platform/control_plane/CompileSpocService.md) + [PolicyEngine.md](implementation/agent_platform/control_plane/PolicyEngine.md) + [ApprovalService.md](implementation/agent_platform/control_plane/ApprovalService.md) + [ModelRouter.md](implementation/agent_platform/control_plane/ModelRouter.md) + [BudgetEnforcer.md](implementation/agent_platform/control_plane/BudgetEnforcer.md) | Phase 2/3: matcher, inference, explainer, compiler; Phase 5: policy, approvals, model routing, budgets |
| `agent_platform.cli` | [module.md](implementation/agent_platform/cli/module.md) | `mas` CLI commands |
| `agent_platform.domain` | [module.md](implementation/agent_platform/domain/module.md) | Phase 3: typed run/project/event domain models |
| `agent_platform.application.ports` | [module.md](implementation/agent_platform/application/ports/module.md) | Phase 3: application ports (plan section 20.1) |
| `agent_platform.adapters` | [module.md](implementation/agent_platform/adapters/module.md) | Phase 3: in-memory/local test-double adapters behind the ports above |
| `agent_platform.execution_plane` | [module.md](implementation/agent_platform/execution_plane/module.md) + [ProjectExecutionFlow.md](implementation/agent_platform/execution_plane/ProjectExecutionFlow.md) + [Worker.md](implementation/agent_platform/execution_plane/Worker.md) + [raid.md](implementation/agent_platform/execution_plane/raid.md) + [status_report_generator.md](implementation/agent_platform/execution_plane/status_report_generator.md) + [flows/module.md](implementation/agent_platform/execution_plane/flows/module.md) | Phase 3: `ProjectExecutionFlow`, QA gate; Phase 6: worker + lease recovery; Phase 7: project-management workflows (G0-G5) |
| `agent_platform.telemetry` | [module.md](implementation/agent_platform/telemetry/module.md) | Phase 3: event JSONL projection, run summary generation; Phase 8: metrics registry (M8.1) |
| `agent_platform.evaluation` | [module.md](implementation/agent_platform/evaluation/module.md) | Phase 8: regression evaluation runner + datasets (M8.2) |
| `agent_platform.security` | [module.md](implementation/agent_platform/security/module.md) | Phase 8: prompt-injection detector (M8.3) |
| `agent_platform.knowledge_graph` | [module.md](implementation/agent_platform/knowledge_graph/module.md) | Phase 9: graph generator + style config (M9.1) |
| `agent_platform.docs` | [module.md](implementation/agent_platform/docs/module.md) | plan 17.8: documentation-as-code analyzer |
| `agent_platform.api` | [module.md](implementation/agent_platform/api/module.md) | Phase 6: FastAPI control plane + SSE/RBAC; Phase 9: graph + chat endpoints (M9.2) |
| `agent_platform.repositories.postgres` | [module.md](implementation/agent_platform/repositories/postgres/module.md) | Phase 6: PostgreSQL RunStateStore/EventLedger |

## Tool library (`tools/`)

These are consumed through the tool registry, not imported as application
code (masterplan section 7.1, 14.1).

| Tool package | Module doc | Notes |
|---|---|---|
| `tools.file_tools` | [module.md](implementation/tools/file_tools/module.md) + [PathGuard.md](implementation/tools/file_tools/PathGuard.md) | Phase 4: path security kernel, scoped read/write, secret scanner |
| `tools.git_tools` | [module.md](implementation/tools/git_tools/module.md) | Phase 4: branch-per-run + pull-request body |
| `tools.validation_tools` | [module.md](implementation/tools/validation_tools/module.md) | Phase 4: checksum manifest + provenance stamping |

100% documentation coverage for required code units is a protected-branch
requirement (plan section 17.8) once CI enforces it; it is not yet enforced
by tooling (`mas docs validate` from plan section 17.8 is not implemented).
This table is the interim, hand-maintained substitute.
