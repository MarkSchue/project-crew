---
schema_version: code-doc/1.0
doc_id: CODE-DOC-MODEL-ROUTER
code_unit_id: CODE-MODEL-ROUTER
title: ModelRouter
code_ref: src/agent_platform/control_plane/model_router.py#ModelRouter
unit_type: application_service
status: active
owner_role: platform_engineering
introduced_in: M5.3
classification: internal
related_requirements: []
related_adrs: [ADR-010]
related_test_cases: []
last_verified_commit: "<generated-by-ci>"
---

# `ModelRouter`

## Purpose

Resolves a SPOC's `default_model_profile` / `routing.model_override`
against the model catalog, enforcing data-residency and classification
constraints as the most restrictive intersection (masterplan section
15.6). A violating combination is rejected at compile time (M3.2), not at
runtime (M5.3 DoD).

## Classification

Security-relevant: this is the control that prevents confidential/
restricted data from reaching an ineligible model provider.

## Responsibilities

- `resolve(profile_id, *, classification, data_residency=None) -> ModelCatalogEntry`
- Reject unknown or non-`active` profiles.
- Reject `confidential` against a profile that is not
  `confidential_eligible`.
- Reject `restricted` outright (no provider eligible by default).
- Reject a `data_residency` the profile does not declare.

## Explicit non-responsibilities

- Does not call any model — it only resolves the catalog entry.
- Does not manage the model catalog itself (that is
  `agent_platform.registries.model_registry`).

## Invariants

- `restricted` classification always fails unless a future policy
  explicitly allows it (currently no profile is eligible).

## Dependencies and dependency direction

Depends on `registries.models.ModelCatalogEntry` and
`registries.model_registry.ModelRegistry`. Depended on by the compiler and
(later) the execution plane's model-gateway adapter.

## Linked test cases and latest accepted evidence

`tests/unit/test_model_router.py` (5 tests) — passing as of the Phase 5
commit.

## Material change history

- 2026-08-24: initial implementation (Phase 5, M5.3).
