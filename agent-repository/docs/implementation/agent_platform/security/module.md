---
schema_version: code-doc/1.0
doc_id: CODE-DOC-SECURITY-MODULE
code_unit_id: CODE-MODULE-SECURITY
title: agent_platform.security
code_ref: src/agent_platform/security/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M8.3
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.security`

## Purpose

Security controls for untrusted content (masterplan section 15.4, plan
milestone M8.3).

## Responsibilities / public contract

- `prompt_injection.py`: `scan_prompt_injection(text)`,
  `has_prompt_injection(text)` — flags instruction-override payloads in
  repository/external content; a finding requires human confirmation
  before any instruction inside a document is acted on (masterplan
  section 15.4).

## Explicit non-responsibilities

- Not a general-purpose content filter; it is a conservative,
  regex-based detector (false positives acceptable — they route to human
  confirmation, not automatic blocking).

## Linked test cases and latest accepted evidence

`tests/security/test_prompt_injection.py` (15 corpus cases), passing as
of the Phase 8 commit.
