---
schema_version: code-doc/1.0
doc_id: CODE-DOC-TELEMETRY-MODULE
code_unit_id: CODE-MODULE-TELEMETRY
title: agent_platform.telemetry
code_ref: src/agent_platform/telemetry/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M3.7, M3.9
classification: internal
related_requirements: []
related_adrs: [ADR-013]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.telemetry`

## Purpose

Portable run evidence: the append-only `events.jsonl` projector and the
human-readable `summary.md` generator (masterplan section 16, ADR-013).

## Responsibilities / public contract

- `event_writer.py`: `project_events_to_jsonl(events, output_path) -> int`
  — appends only events whose `event_id` is not already present; never
  rewrites an existing line (write-once, verified by test).
- `run_summary.py`: `generate_run_summary_markdown(state, events) -> str`
  — produces an OKF `run_summary` with `generated_by` back to the SPOC
  and `evidenced_by` forward to `events.jsonl`, listing every test result
  (masterplan section 9.5, plan M3.9).

## Explicit non-responsibilities

- Not an OpenTelemetry exporter — masterplan section 26 lists
  OpenTelemetry for traces/metrics; that is a Phase 8 concern and is not
  yet wired here.
- Not the authoritative event store — the `EventLedger` port is
  authoritative (ADR-013); this module is the projection.

## Dependencies and dependency direction

Depends on `agent_platform.domain`. Depended on by
`agent_platform.execution_plane` and CLI/test callers.

## Security and data-classification behavior

`RunEvent.payload` must already be redacted by the caller before it is
passed here; this module does not redact (plan section 22.3 redaction is
a projector-input responsibility, documented as such).

## Linked test cases and latest accepted evidence

`tests/unit/test_event_writer.py` (3 tests), `tests/unit/test_run_summary.py`
(2 tests), all passing as of the Phase 3 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 3).
