# Glossary

Controlled platform vocabulary (plan section 17.7). Terms are defined once
here; other documents link back rather than redefining them.

- **OKF (Open Knowledge Format):** the Markdown-plus-YAML-front-matter
  convention for all governed project knowledge (masterplan section 9).
- **SPOC (Supplier, Procedure, Output, Consumer):** the smallest governed
  unit of project execution (masterplan section 10).
- **Run manifest:** the immutable, compiled output of the SPOC compiler; the
  only thing the execution plane is allowed to execute from (masterplan
  section 10.4).
- **`execution_key`:** a deterministic hash of project, SPOC version,
  resolved inputs, workflow version, policy bundle, and idempotency scope
  (plan section 19.2).
- **`run_id`:** one logical execution lifecycle for an `execution_key`
  (plan section 19.2).
- **`attempt_id`:** one processing attempt within a run, including QA
  rework (plan section 19.2).
- **`step_id`:** one Flow step execution (plan section 19.2).
- **`child_run_id`:** a separately governed delegated execution linked to
  its parent (plan section 19.2).
- **Capability:** a named, versioned unit of agent competence (masterplan
  section 12.1), claimed by agents with evidence and required by SPOCs.
- **Hard filter:** a pass/fail precondition in capability matching (agent
  status, classification clearance, tool permissions, etc. — masterplan
  section 12.2). Distinct from the weighted score.
- **Execution mode:** `atomic`, `delegated`, `crew`, or `workflow` — how
  much orchestration a SPOC's procedure needs (plan section 19.3).
- **Port:** an application-layer Protocol/interface (e.g. `RunStateStore`,
  `EventLedger`) that decouples application/domain code from a specific
  infrastructure implementation (plan section 20.1).
- **Adapter:** a concrete implementation of a port (e.g. an in-memory or
  SQLite-backed `RunStateStore`).
- **QA rework loop:** the `review -> rejected -> ready` SPOC state
  transition that returns a failed SPOC to its originating agent, bounded
  by `retry_policy.max_attempts` (masterplan section 10.3, 13.5).
