---
schema_version: code-doc/1.0
doc_id: CODE-DOC-FILE-TOOLS-MODULE
code_unit_id: CODE-MODULE-FILE-TOOLS
title: tools.file_tools
code_ref: tools/file_tools/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M4.1-M4.2
classification: internal
related_requirements: []
related_adrs: [ADR-007, ADR-018]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `tools.file_tools`

## Purpose

The path-security kernel and scoped read/write tools (masterplan section
14.4). These enforce least-privilege file access *independently of any
prompt* (ADR-007: tool-side authorization, not prompt restrictions).

## Classification

Security-critical. This is the enforcement point for the
worker-to-repository trust boundary (threat model T7-T9, T15-T16).

## Responsibilities / public contract

- `path_guard.PathGuard` — canonicalizes paths, rejects outside-root and
  symlink-escape access, and separates read/write permission via an
  allowlist (see its class doc).
- `repository_read.read_bytes(path, path_guard, *, audit, attribution)`
  — read-only access returning bytes + an audit event.
- `repository_write_scoped.write_bytes(path, content, path_guard, *,
  audit, lock_dir, attribution)` — atomic, locked, secret-scanned write;
  returns the content hash; raises `SecretRejectionError` on a secret.
- `secret_scanner.scan_bytes / has_secrets` — conservative regex secret
  detection (AWS keys, private keys, tokens, password assignments).

## Explicit non-responsibilities

- Not a replacement for a dedicated secret-scanning product (gitleaks/
  Bandit integration is a follow-up); it is the deterministic MVP
  rejection path.
- Does not manage Git or provenance (see `tools.git_tools`,
  `tools.validation_tools`).

## Invariants

- Every write is atomic (`os.replace`) and serialized by an advisory
  `flock` on a sidecar lock file.
- A secret-flagged write never touches disk; the rejection is logged as a
  `security_event` before raising.

## Dependencies and dependency direction

Depends on `fcntl` (stdlib) only. Depended on by tests and (later) the
execution plane via the tool registry.

## Security and data-classification behavior

`PathGuard.allowlist` is the manifest-derived least-privilege surface;
longest-prefix rules win, so a more specific read-only rule overrides a
broader write rule.

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

All rejections are typed with a stable `code` (`PATH_OUTSIDE_ROOT`,
`SYMLINK_ESCAPE`, `PERMISSION_DENIED`, `SECRET_REJECTED`).

## Linked test cases and latest accepted evidence

`tests/security/test_path_guard.py`,
`tests/unit/test_repository_read_write.py`,
`tests/security/test_file_mutations.py` — passing as of the Phase 4
commit.

## Material change history

- 2026-08-24: initial implementation (Phase 4).
