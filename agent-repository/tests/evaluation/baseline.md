# Evaluation baseline

Plan milestone M0.5. Describes the initial evaluation baseline and how it
will grow per capability (masterplan section 20.3).

## Current baseline (2026-08-24)

**Empty.** No LLM-backed capability has an evaluation dataset yet. This is
intentional: the MVP vertical slice proves the *control model*
(masterplan section 27), not model quality, and every current test is a
deterministic unit test (ADR-020). No model call is made anywhere in the
repository at this point.

## How it will grow per capability

When a capability is first claimed by a real agent, the activation
checklist (`check_activation_readiness` in
`agent_platform/registries/validators.py`) requires:

1. `health.evaluation_suite` named for that agent.
2. `evidence_refs` on every claimed capability pointing at an evaluation
   fixture (`tests/evaluation/...`).
3. A versioned dataset + rubric recorded here, with model id, prompt
   version hash, tool versions, and a repeated-run policy.

Each capability family then owns a subsection below that records:

- dataset version and provenance/classification (no confidential data
  without review, masterplan section 18.8).
- rubric (pass criteria, prohibited behaviors).
- last measured pass rate vs. the agent's `minimum_pass_rate`.
- known contamination/leakage checks.

## Backlog of capabilities needing baselines (none measured yet)

- `security.oauth2.design`
- `security.threat_model`
- `architecture.solution_documentation`
- `architecture.requirement_traceability`
- `qa.acceptance_validation`
- `qa.traceability_check`

Each entry above must be moved out of this list into a measured subsection
before its claiming agent can be marked `active` with a real model
backend (currently all fixture agents are synthetic).
