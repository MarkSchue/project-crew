---
schema_version: code-doc/1.0
doc_id: CODE-DOC-CLI-MODULE
code_unit_id: CODE-MODULE-CLI
title: agent_platform.cli
code_ref: src/agent_platform/cli/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M1.8, M2.5
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.cli`

## Purpose

The `mas` command-line entry point (masterplan section 17.1, plan M1.8).
Thin wrapper over `agent_platform.schemas` and `agent_platform.registries`;
contains no business logic of its own beyond argument parsing and
presentation (Rich tables).

## Classification

User-facing tool; not a security boundary (it runs with the operator's own
filesystem permissions).

## Responsibilities

- `main.py`: Typer app exposing `mas project validate`, `mas project
  init`, `mas project migrate`, `mas index rebuild`, `mas graph rebuild`,
  `mas registry validate`, `mas agent scaffold`, and `mas chat`.
- `agent_scaffold.py`: generates a schema-valid, `status: draft` agent
  scaffold (masterplan section 11.3); intentionally incomplete until a
  human fills in role/goal/capabilities/evaluations.

## Explicit non-responsibilities

- Does not implement `mas docs *` (plan section 17.8) — not yet built.

## Public contract (commands)

| Command | Behavior | Exit code |
|---|---|---|
| `mas project validate <dir> [--schemas dir] [--mode fast\|full]` | lint + xref-validate every OKF file under `dir` | 0 clean, 1 on any error |
| `mas project init <dir> [--template v]` | copy the pinned project skeleton + write `template.lock` | 0 always (2 if target not empty) |
| `mas project migrate <dir>` | apply pending project migrations | 0 always |
| `mas index rebuild <dir>` | regenerate `index.md` projections | 0 always (unless path missing: 2) |
| `mas graph rebuild <dir> [--style-config f]` | regenerate `public/knowledge/graph_index.json` | 1 on dangling relation or unknown type |
| `mas registry validate <registry-dir> [--schemas dir]` | load all six registries | 0 clean, 1 on `RegistryError` |
| `mas agent scaffold <agent-id> [--registry dir]` | write a draft agent scaffold | 0 always |
| `mas chat [--question q] [--graph f] [--project-root dir]` | one-shot or interactive PM-agent query (read-only) | 0 always |

## Invariants

None beyond what the wrapped modules guarantee.

## Dependencies and dependency direction

Depends on `agent_platform.schemas`, `agent_platform.registries`, `typer`,
`rich`. Nothing depends on `agent_platform.cli` (leaf module).

## Security and data-classification behavior

None — inherits the operator's own file permissions; does not itself
enforce classification rules.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

Every command is a single synchronous invocation; non-zero exit codes are
the only failure signal (no retries).

## Events, metrics, traces, and correlation identifiers

None.

## Linked test cases and latest accepted evidence

Exercised indirectly by `tests/unit/test_agent_scaffold.py`; commands
themselves are smoke-tested manually (see session notes), not yet under a
dedicated CLI contract-test suite (tracked as backlog).

## Material change history

- 2026-08-24: `project validate`, `index rebuild` (Phase 1); `registry
  validate`, `agent scaffold` (Phase 2).
