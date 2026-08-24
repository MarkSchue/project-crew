---
schema_version: code-doc/1.0
doc_id: CODE-DOC-VALIDATION-TOOLS-MODULE
code_unit_id: CODE-MODULE-VALIDATION-TOOLS
title: tools.validation_tools
code_ref: tools/validation_tools/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M4.4
classification: internal
related_requirements: []
related_adrs: [ADR-002]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `tools.validation_tools`

## Purpose

Checksum manifests and provenance stamping (plan milestone M4.4): content
address every produced artifact and stamp generated OKF artifacts with
`provenance.run_id` so they are traceable back to the run that produced
them.

## Classification

Evidence/provenance tooling — supports the Git/OKF-as-authoritative-record
principle (ADR-002).

## Responsibilities / public contract

- `checksum_manifest.build_checksum_manifest(run_id, artifacts) -> dict`
- `checksum_manifest.write_checksum_manifest(checksums_dir, run_id,
  artifacts) -> Path` — writes `artifacts/checksums/<run_id>.json`
- `checksum_manifest.stamp_okf_provenance(markdown_text, run_id) -> str`
  — sets `provenance.run_id` in OKF front matter, preserving the body
- `checksum_manifest.stamp_okf_file(path, run_id)`

## Explicit non-responsibilities

- Does not validate OKF schema (that is `agent_platform.schemas`).
- Does not compute the *run manifest* hash (that is
  `agent_platform.control_plane.spoc_compiler`).

## Invariants

- `build_checksum_manifest` is deterministic (sorted keys and refs).
- `stamp_okf_provenance` never alters the Markdown body.

## Dependencies and dependency direction

Stdlib only. Depended on by tests and (later) the run finalization step.

## Linked test cases and latest accepted evidence

`tests/unit/test_checksum_manifest.py` — passing as of the Phase 4
commit.

## Material change history

- 2026-08-24: initial implementation (Phase 4, M4.4).
