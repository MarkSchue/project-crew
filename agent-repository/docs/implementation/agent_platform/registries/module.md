---
schema_version: code-doc/1.0
doc_id: CODE-DOC-REGISTRIES-MODULE
code_unit_id: CODE-MODULE-REGISTRIES
title: agent_platform.registries
code_ref: src/agent_platform/registries/
unit_type: module
status: active
owner_role: platform_engineering
introduced_in: M2.1-M2.2
classification: internal
related_requirements: []
related_adrs: [ADR-005, ADR-010]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# Module: `agent_platform.registries`

## Purpose

Loads and validates the six governed registries (masterplan section 7.1,
11-14): capabilities, agents, skills, tools, models, workflows. Exposes
typed Pydantic models to application code instead of raw YAML dicts.

## Classification

Foundational registry/catalog module; depended on by
`agent_platform.control_plane`.

## Responsibilities

- Load YAML registry entries and validate them against the corresponding
  JSON Schema (`base.py: validate_entry`).
- Fail loudly, with every individual error collected, on any invalid or
  dangling reference (`RegistryError`).
- Resolve capability aliases and transitively expand `requires`
  dependencies (`capability_registry.py`).
- Provide semantic-version, deprecation-metadata, evidence, and
  activation-readiness checks that schemas alone cannot express
  (`validators.py`).
- Separate runtime health (observed pass rate) from static agent
  definition (`health.py`) — an unhealthy agent is reported unhealthy, not
  removed from the registry.

## Explicit non-responsibilities

- Does not perform capability matching/scoring — see
  `agent_platform.control_plane.capability_matcher`.
- Does not enforce tool-call authorization at runtime — that is the
  Phase 4/5 policy engine (ADR-007, ADR-016), not yet implemented.

## Public contract

- `load_capability_registry(registry_dir, schema_registry) -> CapabilityRegistry`
- `load_agent_registry(registry_dir, schema_registry, capability_registry) -> AgentRegistry`
  (raises `RegistryError` on any dangling capability reference or
  duplicate `agent_id`)
- `load_skill_registry`, `load_tool_registry`, `load_model_registry`,
  `load_workflow_registry` (workflows keyed by `(workflow_id, version)`
  per ADR-015's three-artifact contract; this registry is only the
  metadata layer, not the Python Flow implementation)
- `validators.check_semantic_version`, `check_deprecation_metadata`,
  `check_capability_evidence`, `check_activation_readiness`
- `health.evaluate_health(agent, observed_pass_rate) -> HealthStatus`

## Invariants

- An agent's claimed capability IDs always resolve in the capability
  registry, or loading fails.
- `deprecated_by` is set if and only if `status == "deprecated"`.

## State and lifecycle

Stateless loaders; the returned registry objects are immutable snapshots
of the YAML files at load time (no live file-watching).

## Concurrency and transaction assumptions

None — single-process load; registries are re-loaded per CLI invocation.

## Dependencies and dependency direction

Depends on `agent_platform.schemas` (SchemaRegistry) and `pydantic`.
Depended on by `agent_platform.control_plane` and `agent_platform.cli`.

## Security and data-classification behavior

`allowed_classifications` on `AgentDefinition` is read but not yet
enforced at runtime (enforcement is a Phase 4/5 concern).

## Failure, timeout, retry, cancellation, idempotency, and recovery behavior

Synchronous; any validation failure raises `RegistryError` with the full
list of collected error strings rather than failing on the first one.

## Events, metrics, traces, and correlation identifiers

None yet.

## Minimal usage example

```python
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.agent_registry import load_agent_registry

capability_registry = load_capability_registry(registry_dir, schema_registry)
agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
```

## Linked requirements, ADRs, workflows, and schemas

ADR-005 (deterministic capability matching depends on this registry
layer), ADR-010 (versioning). Schemas: `agent.schema.json`,
`capability.schema.json`, `skill.schema.json`, `tool.schema.json`,
`model_catalog.schema.json`, `workflow_catalog.schema.json`.

## Linked test cases and latest accepted evidence

`agent-repository/tests/unit/test_registries.py` — passing as of the
Phase 2 commit.

## Material change history

- 2026-08-24: initial implementation (Phase 2).
