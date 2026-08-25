# Performance and cost optimization pass

**Owner role:** platform_engineering · **Introduced:** M8.5
**Measured:** `ops/profiling/bench.py` → `ops/profiling/result.json` (real
numbers, not estimates).

## Measured hot paths (vertical-slice, 2026-08-24)

| Operation | Measured |
|---|---|
| Registry load (schemas + 3 agents + 10 capabilities + workflows) | ~0.0298 s |
| SPOC compilation | ~0.0007 s |
| SQLite 50 saves + 50 event appends | ~0.0141 s |
| Full flow run (no model calls) | ~0.0013 s |

## Findings

1. **Top contributor: per-operation SQLite commits.** The SQLite adapters
   commit once per `save`/`append` (ADR-013 makes the database the
   authoritative ledger, and each write is made durable immediately).
   Under load this is the dominant write cost and scales linearly with
   event volume.
2. **Registry load is a one-time fixed cost** dominated by JSON-schema
   compilation and YAML parsing; negligible in steady state.
3. **Model/tool calls are not yet measured** because no real model adapter
   exists (masterplan section 28.6). Once CrewAI is wired in, model calls
   are expected to dominate both cost and latency; the economics metrics
   (`cost_per_accepted_spoc_usd`, `rework_cost_usd`) are instrumented in
   M8.1 for that day.

## Prioritized optimization backlog

| # | Item | Expected impact | Decision |
|---|---|---|---|
| 1 | Batch SQLite commits per flow step (transaction scope) instead of per write | Removes most write amplification | **Deferred — owned** |
| 2 | Cache the compiled `SchemaRegistry` across CLI/API processes | Saves ~0.03 s per cold start | Backlog |
| 3 | Measure and cap model/tool call cost once a real model adapter lands | TBD until CrewAI integration | Backlog |

## Deferral record (top bottleneck)

- **Item:** batch SQLite commits (per-write durability → per-step
  transaction).
- **Owner:** `platform_engineering`.
- **Reason for deferral:** ADR-013 requires the event ledger to be
  durable and authoritative; changing commit granularity changes the
  crash-window/durability tradeoff and must land together with the
  PostgreSQL adapter and retention enforcement (M8.7), not in isolation.
- **Trigger to revisit:** before Phase 9's Project Manager chat lands,
  because chat-session events will sharply increase event volume.

No production latency/cost SLAs are claimed from these vertical-slice
measurements.
