"""Run/attempt/step identity model (plan section 19.2, ADR-014).

A stable identity model used consistently across the compiler, the
execution flow, the event ledger, and the run-state store:

- ``spoc_id`` / ``spoc_version``: the governed work package being executed.
- ``execution_key``: deterministic hash of project, SPOC version, resolved
  inputs, workflow version, policy bundle, and idempotency scope.
- ``run_id``: one logical execution lifecycle for an ``execution_key``.
- ``attempt_id``: one processing attempt within a run (including QA
  rework); a new ``attempt_id`` is created for rework, not a new
  ``run_id``.
- ``step_id``: one Flow step execution.
- ``child_run_id``: a separately governed delegated execution linked to
  its parent.

This module has no dependency on CrewAI, FastAPI, SQLAlchemy, Git, any
cloud SDK, or any model-provider package (plan section 20.2).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def compute_execution_key(
    *,
    project_id: str,
    spoc_id: str,
    spoc_version: str,
    resolved_input_hashes: list[str],
    workflow_id: str,
    workflow_version: str,
    policy_bundle_version: str,
    idempotency_scope: str = "",
) -> str:
    """Deterministic hash of everything that defines "the same execution"
    (plan section 19.2). Two calls with identical arguments always return
    the same key; changing any material input changes it."""
    canonical = "|".join(
        [
            project_id,
            spoc_id,
            spoc_version,
            ",".join(sorted(resolved_input_hashes)),
            workflow_id,
            workflow_version,
            policy_bundle_version,
            idempotency_scope,
        ]
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"execkey_{digest[:32]}"


@dataclass(frozen=True)
class RunIdentity:
    project_id: str
    spoc_id: str
    spoc_version: str
    execution_key: str
    run_id: str
    attempt_id: str
    correlation_id: str
    parent_run_id: str | None = None

    def with_new_attempt(self, attempt_id: str) -> "RunIdentity":
        """Return a copy identifying a new attempt under the same run
        (QA rework, plan section 19.2)."""
        return RunIdentity(
            project_id=self.project_id,
            spoc_id=self.spoc_id,
            spoc_version=self.spoc_version,
            execution_key=self.execution_key,
            run_id=self.run_id,
            attempt_id=attempt_id,
            correlation_id=self.correlation_id,
            parent_run_id=self.parent_run_id,
        )
