from pathlib import Path

import pytest

from agent_platform.control_plane.capability_matcher import (
    MatchRequest,
    UnknownCapabilityError,
    match,
)
from agent_platform.registries.agent_registry import AgentRegistry, load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.models import AgentCapabilityClaim, AgentDefinition
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def registry_dir(fixtures_dir) -> Path:
    return fixtures_dir / "registry"


@pytest.fixture
def loaded_registries(schema_dir, registry_dir):
    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    return agent_registry, capability_registry


def test_single_agent_covers_all_required_capabilities(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["qa.acceptance_validation", "qa.traceability_check"],
        classification="internal",
    )
    result = match(request, agent_registry, capability_registry)

    assert result.primary is not None
    assert result.primary.agent_id == "qa_evaluator"
    assert not result.delegate_candidates
    assert not result.unresolved_capabilities
    assert result.fully_covered_by_primary


def test_two_capabilities_split_across_two_agents_produces_delegate(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["security.oauth2.design", "architecture.solution_documentation"],
        classification="internal",
    )
    result = match(request, agent_registry, capability_registry)

    assert result.primary is not None
    assert result.primary.agent_id == "security_architect"
    assert len(result.delegate_candidates) == 1
    assert result.delegate_candidates[0].agent_id == "architecture_writer"
    assert not result.unresolved_capabilities


def test_unknown_capability_raises(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(explicit_capabilities=["totally.unknown.capability"])
    with pytest.raises(UnknownCapabilityError):
        match(request, agent_registry, capability_registry)


def test_classification_denied_rejects_all_agents(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["qa.acceptance_validation"],
        classification="restricted",
    )
    result = match(request, agent_registry, capability_registry)

    assert result.primary is None
    assert result.unresolved_capabilities == {"qa.acceptance_validation"}


def test_excluded_agent_is_rejected_with_reason(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["qa.acceptance_validation", "qa.traceability_check"],
        classification="internal",
        excluded_agents=["qa_evaluator"],
    )
    result = match(request, agent_registry, capability_registry)

    # No other agent has these capabilities, so no primary is found.
    assert result.primary is None
    rejection_reasons = {r.agent_id: r.reason for r in result.rejected}
    assert rejection_reasons.get("qa_evaluator") == "excluded_by_spoc"


def _make_fake_agent(agent_id: str) -> AgentDefinition:
    return AgentDefinition.model_validate(
        {
            "schema_version": "agent/1.1",
            "agent_id": agent_id,
            "version": "1.0.0",
            "name": agent_id,
            "status": "active",
            "role": "role",
            "goal": "goal",
            "capabilities": [
                AgentCapabilityClaim(id="qa.acceptance_validation", proficiency=4, evidence_refs=["x"])
            ],
            "allowed_tools": [],
            "allowed_classifications": ["internal"],
            "health": {"evaluation_suite": "suite", "minimum_pass_rate": 0.9},
        }
    )


def test_tie_break_is_deterministic_by_lowest_agent_id(loaded_registries):
    _, capability_registry = loaded_registries
    agent_b = _make_fake_agent("zzz_agent")
    agent_a = _make_fake_agent("aaa_agent")
    registry = AgentRegistry(entries={"zzz_agent": agent_b, "aaa_agent": agent_a})

    request = MatchRequest(explicit_capabilities=["qa.acceptance_validation"], classification="internal")
    result = match(request, registry, capability_registry)

    assert result.primary.agent_id == "aaa_agent"

    # Run again to confirm no randomness / reproducibility.
    result2 = match(request, registry, capability_registry)
    assert result2.primary.agent_id == "aaa_agent"
