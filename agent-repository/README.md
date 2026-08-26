# agent-repository

Reusable agent definitions, capabilities, skills, tools, policies, runtime
adapters, and global knowledge for the CrewAI multi-agent project delivery
platform.

**Rule:** Agent definitions and reusable code are versioned here. Active
project artifacts never live here.

See `/plan/crewai_multi_agent_project_masterplan.md` (architecture) and
`/plan/implementation_plan_enhanced_v1.1.md` (milestones) at the workspace
root for the full specification. This package currently implements the
Phase 0/Phase 1 foundation:

- `agent_platform.schemas.canonicalize` — deterministic canonicalization and
  `sha256` content hashing for OKF/SPOC front matter (masterplan §9.2).
- `agent_platform.schemas.okf_linter` — validates OKF Markdown files against
  the JSON Schemas in `project-template-repository/schemas/` and enforces the
  `part_of`/`tested_by` coverage rule from masterplan §9.7.
- `agent_platform.schemas.xref_validator` — builds a global ID index across a
  directory tree and validates that every `relations[].target` resolves to a
  known ID with a type-compatible relation (masterplan §9.3, plan §23.1).
- `agent_platform.schemas.index_generator` — regenerates per-directory
  `index.md` projections from front matter (masterplan §9.4), idempotently.
- `agent_platform.cli.main` — the `mas` CLI (`mas project validate`,
  `mas index rebuild`).

## Development

```bash
cd agent-repository
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Using the platform

If you are a **project manager** (not a platform developer), start with
[`docs/pm_handbook.md`](docs/pm_handbook.md) — quick start, creating a
project, adding agents, the OKF layout, stage gates, SPOCs, QA, and the
web UI.

## CLI quick start

```bash
mas project validate ../active-project-repo/public --schemas ../project-template-repository/schemas
mas index rebuild ../active-project-repo/public
```
