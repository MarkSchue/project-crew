"""Registry semantic validators (masterplan section 11.2, plan M2.2/M2.5).

These run *after* JSON-Schema validation and check governance rules that
schema constraints alone cannot express: evidence-backed capability
claims, deprecation/replacement metadata consistency, and activation
readiness for scaffolded (draft) agents.
"""

from __future__ import annotations

import re

from agent_platform.registries.models import AgentDefinition

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

TODO_MARKER = "TODO"


def check_semantic_version(version: str, *, context: str) -> list[str]:
    if not SEMVER_RE.match(version):
        return [f"{context}: '{version}' is not a valid semantic version (MAJOR.MINOR.PATCH)"]
    return []


def check_deprecation_metadata(status: str, deprecated_by: str | None, *, context: str) -> list[str]:
    """masterplan section 11.2: "Deprecation and replacement metadata"."""
    if status == "deprecated" and not deprecated_by:
        return [f"{context}: status is 'deprecated' but 'deprecated_by' is not set"]
    if status != "deprecated" and deprecated_by:
        return [f"{context}: 'deprecated_by' is set but status is '{status}', not 'deprecated'"]
    return []


def check_capability_evidence(agent: AgentDefinition) -> list[str]:
    """masterplan section 11.2: "Evaluation evidence for claimed
    capabilities". M2.2 DoD: an agent claiming a capability with no
    evidence_refs fails validation."""
    errors = []
    for claim in agent.capabilities:
        if not claim.evidence_refs:
            errors.append(
                f"agent '{agent.agent_id}': capability '{claim.id}' has no evidence_refs"
            )
    return errors


def check_activation_readiness(agent: AgentDefinition) -> list[str]:
    """Plan section 17.3 change map (M2.5 row): a scaffolded agent is
    schema-valid as `status: draft`; this stricter check is what blocks the
    draft -> active transition until a human has filled in the
    placeholders left by `mas agent scaffold`."""
    errors = []
    if TODO_MARKER in agent.role:
        errors.append(f"agent '{agent.agent_id}': role still contains a TODO placeholder")
    if TODO_MARKER in agent.goal:
        errors.append(f"agent '{agent.agent_id}': goal still contains a TODO placeholder")
    if not agent.capabilities:
        errors.append(f"agent '{agent.agent_id}': no capabilities declared")
    errors.extend(check_capability_evidence(agent))
    if not agent.health.evaluation_suite:
        errors.append(f"agent '{agent.agent_id}': no health.evaluation_suite declared")
    return errors
