"""Deterministic capability matcher (masterplan section 3.3, 12.2, 12.4;
plan milestone M2.3).

Four-stage process:

1. Validate explicit capabilities against the capability registry.
2. Expand aliases and dependencies.
3. (Optional, separate step) LLM-proposed candidate capabilities — see
   ``capability_inference.py``. Not merged in automatically here; the
   caller decides whether to fold approved inferred capabilities into the
   requested set before matching.
4. Apply deterministic hard filters and a weighted score.

Weights are configuration, not hard-coded policy (masterplan section
12.2), but MVP defaults are provided here. Per plan section 17.1 medium
finding 5 ("capability relevance based on project context needs a
deterministic feature definition or must be disabled in MVP scoring"),
``relevant_project_context`` is fixed at weight 0.0 until a deterministic
feature definition exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_platform.registries.agent_registry import AgentRegistry
from agent_platform.registries.capability_registry import CapabilityRegistry
from agent_platform.registries.health import evaluate_health
from agent_platform.registries.models import AgentDefinition

# Default scoring weights (masterplan section 12.2), with
# relevant_project_context disabled for MVP (plan section 17.1, medium
# finding 5).
DEFAULT_WEIGHTS: dict[str, float] = {
    "capability_coverage": 0.35,
    "evaluation_quality": 0.20,
    "relevant_project_context": 0.0,  # disabled for MVP, see module docstring
    "tool_compatibility": 0.10,
    "model_fit": 0.10,
    "availability": 0.05,
    "cost_efficiency": 0.05,
}


class UnknownCapabilityError(ValueError):
    """Raised when a SPOC references a capability id that does not exist
    in the capability registry (masterplan section 10.4 compiler step 4)."""


@dataclass
class MatchRequest:
    explicit_capabilities: list[str]
    classification: str = "internal"
    excluded_agents: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    observed_pass_rates: dict[str, float] = field(default_factory=dict)
    availability: dict[str, bool] = field(default_factory=dict)
    cost_estimates_usd: dict[str, float] = field(default_factory=dict)
    max_total_cost_usd: float | None = None
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


@dataclass
class Candidate:
    agent_id: str
    score: float
    score_breakdown: dict[str, float]
    covered_capabilities: set[str]


@dataclass
class Rejected:
    agent_id: str
    reason: str


@dataclass
class MatchResult:
    required_capabilities: set[str]
    ranked: list[Candidate]
    rejected: list[Rejected]
    primary: Candidate | None
    delegate_candidates: list[Candidate] = field(default_factory=list)
    unresolved_capabilities: set[str] = field(default_factory=set)

    @property
    def fully_covered_by_primary(self) -> bool:
        return bool(self.primary) and not self.unresolved_capabilities


def _resolve_required_capabilities(
    explicit_capabilities: list[str], capability_registry: CapabilityRegistry
) -> set[str]:
    resolved: set[str] = set()
    for capability_id in explicit_capabilities:
        canonical = capability_registry.resolve(capability_id)
        if canonical not in capability_registry:
            raise UnknownCapabilityError(
                f"unknown capability '{capability_id}' (resolved to '{canonical}')"
            )
        resolved.add(canonical)
    return capability_registry.expand_dependencies(resolved)


def _agent_capability_map(agent: AgentDefinition) -> dict[str, int]:
    return {claim.id: claim.proficiency for claim in agent.capabilities}


def _capabilities_covered_by_agent(
    agent: AgentDefinition,
    capability_registry: CapabilityRegistry,
    candidate_capabilities: set[str],
) -> set[str]:
    """Return the subset of `candidate_capabilities` that `agent` satisfies
    at or above the capability's declared `minimum_proficiency` (if any)."""
    capability_map = _agent_capability_map(agent)
    covered = set()
    for capability_id in candidate_capabilities:
        proficiency = capability_map.get(capability_id)
        if proficiency is None:
            continue
        entry = capability_registry.get(capability_id)
        minimum = entry.minimum_proficiency if entry else None
        if minimum is None or proficiency >= minimum:
            covered.add(capability_id)
    return covered


def _hard_filter_reason(
    agent: AgentDefinition,
    request: MatchRequest,
    capability_registry: CapabilityRegistry,
    required_capabilities: set[str],
    *,
    require_full_coverage: bool,
) -> str | None:
    """Return a failing-hard-filter reason, or None if the agent passes."""
    if agent.agent_id in request.excluded_agents:
        return "excluded_by_spoc"

    if agent.status != "active":
        return f"agent_status:{agent.status}"

    health = evaluate_health(agent, request.observed_pass_rates.get(agent.agent_id))
    if not health.healthy:
        return f"unhealthy:{health.reason}"

    if request.classification not in agent.allowed_classifications:
        return f"classification_denied:{request.classification}"

    for tool_id in request.required_tools:
        if tool_id not in agent.allowed_tools:
            return f"tool_missing:{tool_id}"

    if require_full_coverage:
        capability_map = _agent_capability_map(agent)
        for capability_id in required_capabilities:
            proficiency = capability_map.get(capability_id)
            if proficiency is None:
                return f"capability_missing:{capability_id}"
            entry = capability_registry.get(capability_id)
            minimum = entry.minimum_proficiency if entry else None
            if minimum is not None and proficiency < minimum:
                return f"insufficient_proficiency:{capability_id}"

    estimated_cost = request.cost_estimates_usd.get(agent.agent_id)
    if (
        request.max_total_cost_usd is not None
        and estimated_cost is not None
        and estimated_cost > request.max_total_cost_usd
    ):
        return "cost_infeasible"

    return None


def _score_agent(
    agent: AgentDefinition,
    request: MatchRequest,
    capability_registry: CapabilityRegistry,
    covered_capabilities: set[str],
) -> tuple[float, dict[str, float]]:
    weights = request.weights
    capability_map = _agent_capability_map(agent)

    if covered_capabilities:
        capability_coverage = sum(
            capability_map.get(cid, 0) / 5 for cid in covered_capabilities
        ) / len(covered_capabilities)
    else:
        capability_coverage = 0.0

    evaluation_quality = agent.health.minimum_pass_rate
    if evaluation_quality is None:
        evaluation_quality = 0.5

    relevant_project_context = 0.0  # disabled for MVP, see module docstring

    if request.required_tools:
        present = sum(1 for t in request.required_tools if t in agent.allowed_tools)
        tool_compatibility = present / len(request.required_tools)
    else:
        tool_compatibility = 1.0

    model_fit = 1.0 if agent.default_model_profile else 0.5

    availability = 1.0 if request.availability.get(agent.agent_id, True) else 0.0

    cost_estimate = request.cost_estimates_usd.get(agent.agent_id)
    if cost_estimate is None:
        cost_efficiency = 1.0
    elif request.max_total_cost_usd:
        cost_efficiency = max(0.0, 1.0 - (cost_estimate / request.max_total_cost_usd))
    else:
        cost_efficiency = 1.0

    risk_penalties = 0.0  # no inferred capabilities are considered in this call

    breakdown = {
        "capability_coverage": weights["capability_coverage"] * capability_coverage,
        "evaluation_quality": weights["evaluation_quality"] * evaluation_quality,
        "relevant_project_context": weights["relevant_project_context"] * relevant_project_context,
        "tool_compatibility": weights["tool_compatibility"] * tool_compatibility,
        "model_fit": weights["model_fit"] * model_fit,
        "availability": weights["availability"] * availability,
        "cost_efficiency": weights["cost_efficiency"] * cost_efficiency,
        "risk_penalties": -risk_penalties,
    }
    score = sum(breakdown.values())
    return score, breakdown


def match(
    request: MatchRequest,
    agent_registry: AgentRegistry,
    capability_registry: CapabilityRegistry,
) -> MatchResult:
    required_capabilities = _resolve_required_capabilities(
        request.explicit_capabilities, capability_registry
    )

    ranked: list[Candidate] = []
    rejected: list[Rejected] = []

    for agent in agent_registry:
        reason = _hard_filter_reason(
            agent, request, capability_registry, required_capabilities, require_full_coverage=True
        )
        if reason is not None:
            rejected.append(Rejected(agent_id=agent.agent_id, reason=reason))
            continue
        score, breakdown = _score_agent(agent, request, capability_registry, required_capabilities)
        ranked.append(
            Candidate(
                agent_id=agent.agent_id,
                score=score,
                score_breakdown=breakdown,
                covered_capabilities=set(required_capabilities),
            )
        )

    # Deterministic ordering: score desc, then agent_id ascending (tie-break).
    ranked.sort(key=lambda c: (-c.score, c.agent_id))

    if ranked:
        return MatchResult(
            required_capabilities=required_capabilities,
            ranked=ranked,
            rejected=rejected,
            primary=ranked[0],
        )

    # No single agent covers every required capability: attempt a
    # primary + delegate composition (masterplan section 12.4).
    return _match_with_delegation(request, agent_registry, capability_registry, required_capabilities, rejected)


def _match_with_delegation(
    request: MatchRequest,
    agent_registry: AgentRegistry,
    capability_registry: CapabilityRegistry,
    required_capabilities: set[str],
    full_coverage_rejections: list[Rejected],
) -> MatchResult:
    partial_candidates: list[tuple[Candidate, set[str]]] = []
    partial_rejected: list[Rejected] = []

    for agent in agent_registry:
        reason = _hard_filter_reason(
            agent, request, capability_registry, required_capabilities, require_full_coverage=False
        )
        if reason is not None:
            partial_rejected.append(Rejected(agent_id=agent.agent_id, reason=reason))
            continue
        covered = _capabilities_covered_by_agent(agent, capability_registry, required_capabilities)
        if not covered:
            continue
        score, breakdown = _score_agent(agent, request, capability_registry, covered)
        candidate = Candidate(
            agent_id=agent.agent_id, score=score, score_breakdown=breakdown, covered_capabilities=covered
        )
        partial_candidates.append((candidate, covered))

    if not partial_candidates:
        return MatchResult(
            required_capabilities=required_capabilities,
            ranked=[],
            rejected=full_coverage_rejections,
            primary=None,
            unresolved_capabilities=set(required_capabilities),
        )

    # Choose the primary as the agent covering the most capabilities,
    # tie-broken by score desc, then agent_id ascending.
    partial_candidates.sort(key=lambda pair: (-len(pair[1]), -pair[0].score, pair[0].agent_id))
    primary_candidate, primary_covered = partial_candidates[0]

    remaining = required_capabilities - primary_covered
    delegate_candidates: list[Candidate] = []
    unresolved = set(remaining)

    if remaining:
        best_delegate: tuple[Candidate, set[str]] | None = None
        for candidate, covered in partial_candidates[1:]:
            overlap = covered & remaining
            if not overlap:
                continue
            if best_delegate is None or len(overlap) > len(best_delegate[1] & remaining):
                best_delegate = (candidate, overlap)
        if best_delegate is not None:
            delegate_candidates.append(best_delegate[0])
            unresolved = remaining - best_delegate[1]

    return MatchResult(
        required_capabilities=required_capabilities,
        ranked=[c for c, _ in partial_candidates],
        rejected=partial_rejected,
        primary=primary_candidate,
        delegate_candidates=delegate_candidates,
        unresolved_capabilities=unresolved,
    )
