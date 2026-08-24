---
schema_version: code-doc/1.0
doc_id: CODE-DOC-SCHEMAS-MODULE
code_unit_id: CODE-MODULE-SCHEMAS
title: agent_platform.schemas
code_ref: src/agent_platform/schemas/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M1.2-M1.6
classification: internal
related_requirements: []
related_adrs: [ADR-002, ADR-010]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.schemas`

## Purpose

Deterministic, framework-independent validation and projection logic for
Open Knowledge Format (OKF) and SPOC Markdown files (masterplan section 9,
10). This module is imported by both the CLI and (later) the control
plane; it has no CrewAI, FastAPI, or database dependency (plan section
20.2 dependency rule).

## Classification

Foundational/shared utility module — every later phase depends on it.

## Responsibilities

- Parse OKF front matter and compute deterministic content hashes
  (`canonicalize.py`).
- Validate front matter against the JSON Schemas in
  `project-template-repository/schemas/` and enforce OKF-specific lint
  rules that schema validation alone cannot express (`okf_linter.py`).
- Build a global ID index and validate `relations[]` targets/types
  (`xref_validator.py`).
- Regenerate per-directory `index.md` projections idempotently
  (`index_generator.py`).

## Explicit non-responsibilities

- Does not resolve registry entries (agents, capabilities) — see
  `agent_platform.registries`.
- Does not perform capability matching or SPOC compilation — see
  `agent_platform.control_plane`.
- Does not write to Git or enforce path-security policy — that is a
  Phase 4 concern (`agent-repository/tools/file_tools`, not yet built).

## Public contract

### `canonicalize.py`

- `split_front_matter(text) -> (front_matter_yaml, body)`: raises
  `FrontMatterError` if the `---` delimiters are missing/unclosed.
- `parse_okf_text(text, path=None) -> OkfDocument`: raises
  `FrontMatterError` on invalid YAML or a non-mapping front matter.
- `load_okf_file(path) -> OkfDocument`.
- `compute_content_hash(front_matter, body) -> "sha256:<hex>"`:
  deterministic; excludes `content_hash` itself from its own input.
- `verify_content_hash(document) -> bool`: `True` if no hash is declared,
  or if the declared hash matches the recomputed one.

### `okf_linter.py`

- `SchemaRegistry(schema_dir)`: loads and cross-resolves every
  `*.schema.json` file in a directory (uses the `referencing` library, not
  the deprecated `jsonschema.RefResolver`).
- `lint_document(document, registry) -> list[LintIssue]`,
  `lint_directory(root, registry) -> LintResult`.
- Lint codes: `OKF-SCHEMA-001` (schema violation), `OKF-ID-001` (duplicate
  id), `OKF-COVERAGE-001` (user_story with no `tested_by` relation, error),
  `OKF-COVERAGE-002` (SPOC acceptance criterion with no `test_case_refs`,
  warning only).

### `xref_validator.py`

- `build_id_index(root) -> dict[id, OkfDocument]`.
- `validate_cross_references(root) -> XrefResult`.
- Codes: `OKF-XREF-001` (relation target id does not exist),
  `OKF-XREF-002` (relation target exists but has an incompatible `type`
  for that relation, per the `RELATION_TARGET_TYPES` table).

### `index_generator.py`

- `generate_index_for_directory(directory) -> str | None`.
- `rebuild_indexes(root) -> list[Path]`: idempotent — running twice on an
  unchanged tree produces byte-identical output (verified by test).

## Invariants

- Content hashing is deterministic and canonicalization-order-independent
  (sorted JSON keys, stable separators).
- `index.md` files are pure projections; nothing in this module reads them
  as a source of truth.

## State and lifecycle

Stateless; every function takes explicit input and returns a result or
raises.

## Concurrency and transaction assumptions

None — designed for single-process, single-invocation CLI use. Concurrent
writers to the same `index.md` are not addressed here (see plan section
23.3 for the Git-level answer).

## Dependencies and dependency direction

Depends on `pyyaml`, `jsonschema`, `referencing`. Depended on by
`agent_platform.registries`, `agent_platform.control_plane`,
`agent_platform.cli`. No reverse dependency.

## Security and data-classification behavior

None directly; does not interpret `classification` beyond validating that
the field is one of the four allowed enum values.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

All operations are synchronous, in-process, and side-effect-free except
`rebuild_indexes`, which only writes a file if its content actually
changed (idempotent write).

## Events, metrics, traces, and correlation identifiers

None yet; this module predates the Phase 3 event ledger.

## Minimal usage example

```python
from agent_platform.schemas.okf_linter import SchemaRegistry, lint_directory

registry = SchemaRegistry(Path("project-template-repository/schemas"))
result = lint_directory(Path("plan/decisions"), registry)
assert result.ok
```

## Linked requirements, ADRs, workflows, and schemas

ADR-002 (Git/OKF as authoritative record), ADR-010 (versioning
discipline). Schemas: `okf.schema.json`, `relations.schema.json`,
`spoc.schema.json`.

## Linked test cases and latest accepted evidence

`agent-repository/tests/unit/test_canonicalize.py`,
`test_okf_linter.py`, `test_xref_validator.py`, `test_index_generator.py`
— 21 passing tests as of the Phase 1 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 1 foundation).
