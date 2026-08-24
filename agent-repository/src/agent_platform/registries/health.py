"""Runtime health status, separate from static agent definition
(masterplan section 11.2: "Runtime health status separate from static
definition"; M2.2 DoD: an unhealthy agent is reported unhealthy, not
removed from the registry).
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.registries.models import AgentDefinition


@dataclass(frozen=True)
class HealthStatus:
    agent_id: str
    healthy: bool
    observed_pass_rate: float | None
    minimum_pass_rate: float | None
    reason: str


def evaluate_health(agent: AgentDefinition, observed_pass_rate: float | None) -> HealthStatus:
    """Compare an agent's observed evaluation-suite pass rate against its
    declared `health.minimum_pass_rate`. If no observation is available
    yet, the agent is treated as healthy-by-default (new agents have not
    accumulated evaluation history)."""
    minimum = agent.health.minimum_pass_rate

    if observed_pass_rate is None:
        return HealthStatus(
            agent_id=agent.agent_id,
            healthy=True,
            observed_pass_rate=None,
            minimum_pass_rate=minimum,
            reason="no evaluation history yet",
        )

    if minimum is None:
        return HealthStatus(
            agent_id=agent.agent_id,
            healthy=True,
            observed_pass_rate=observed_pass_rate,
            minimum_pass_rate=None,
            reason="no minimum_pass_rate declared",
        )

    healthy = observed_pass_rate >= minimum
    reason = (
        f"observed pass rate {observed_pass_rate:.2f} >= minimum {minimum:.2f}"
        if healthy
        else f"observed pass rate {observed_pass_rate:.2f} < minimum {minimum:.2f}"
    )
    return HealthStatus(
        agent_id=agent.agent_id,
        healthy=healthy,
        observed_pass_rate=observed_pass_rate,
        minimum_pass_rate=minimum,
        reason=reason,
    )
