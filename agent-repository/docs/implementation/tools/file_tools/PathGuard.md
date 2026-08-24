---
schema_version: code-doc/1.0
doc_id: CODE-DOC-PATH-GUARD
code_unit_id: CODE-PATH-GUARD
title: PathGuard
code_ref: tools/file_tools/path_guard.py#PathGuard
unit_type: security_kernel
status: active
owner_role: platform_engineering
introduced_in: M4.1
classification: internal
related_requirements: []
related_adrs: [ADR-007]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `PathGuard`

## Purpose

The path security kernel: the single choke point through which every file
read/write tool must pass before touching the filesystem (masterplan
section 14.4).

## Classification

Security-critical internal class; documented even though it is a small
helper, because it is the primary technical control against path
traversal and symlink escape.

## Responsibilities

- Canonicalize and resolve paths.
- Reject access outside configured mount roots (`PathOutsideRootError`).
- Reject symlinks whose resolved target escapes the roots
  (`SymlinkEscapeError`).
- Enforce read vs. write permission from an allowlist, with
  longest-prefix-wins semantics (`PermissionDeniedError`).

## Explicit non-responsibilities

- Does not read/write files itself — it only authorizes a path.
- Does not scan secrets (that is `tools.file_tools.secret_scanner`).

## Public contract

- `PathGuard(mount_roots, allowlist)` — `allowlist` maps an absolute path
  string to `"read"` or `"write"`.
- `assert_read(path) -> Path` — resolved path or a typed error.
- `assert_write(path) -> Path` — resolved path or a typed error.

## Invariants

- A write never succeeds for a path whose most-specific allowlist entry
  grants only `"read"`.

## Failure behavior

Typed exceptions with stable codes: `PATH_OUTSIDE_ROOT`,
`SYMLINK_ESCAPE`, `PERMISSION_DENIED`.

## Dependencies and dependency direction

Stdlib only. Depended on by `repository_read` and
`repository_write_scoped`.

## Linked test cases and latest accepted evidence

`tests/security/test_path_guard.py` — covers `../../etc/passwd`
traversal, in-root symlink escape, read-only write denial, and
longest-prefix override (all passing as of the Phase 4 commit).

## Material change history

- 2026-08-24: initial implementation (Phase 4, M4.1).
