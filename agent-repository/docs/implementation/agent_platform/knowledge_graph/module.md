---
schema_version: code-doc/1.0
doc_id: CODE-DOC-KNOWLEDGE-GRAPH-MODULE
code_unit_id: CODE-MODULE-KNOWLEDGE-GRAPH
title: agent_platform.knowledge_graph
code_ref: src/agent_platform/knowledge_graph/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M9.1
classification: internal
related_requirements: []
related_adrs: []
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.knowledge_graph`

## Purpose

The regenerable knowledge-graph projection (masterplan section 9.6, plan
milestone M9.1). Walks OKF files plus non-OKF evidence leaves, builds
nodes/edges, and writes `public/knowledge/graph_index.json`.

## Responsibilities / public contract

- `graph_generator.py`: `generate_graph_index(root, style_config)`,
  `build_and_validate(root, style_config)`, `write_graph_index(...)`,
  `load_style_config(path)`.
- `style_config.yaml`: type -> color/icon table (configuration, not
  hard-coded).

## Invariants

- Idempotent regeneration (byte-identical output on an unchanged tree).
- Every node type resolves to a style entry; unknown types raise.
- A relation targeting an unknown id is a dangling relation and raises.

## Explicit non-responsibilities

- The graph is a projection, never the system of record (masterplan
  section 9.6); OKF Markdown remains authoritative.
- Rendering lives in the web UI (`agent-repository/web/`), not here.

## Linked test cases and latest accepted evidence

`tests/unit/test_graph_generator.py` (5 tests), passing as of the Phase 9
commit.
