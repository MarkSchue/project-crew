from pathlib import Path

import pytest

from agent_platform.control_plane.capability_matcher import MatchRequest, match
from agent_platform.control_plane.match_explainer import explain_match_json, explain_match_markdown
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def loaded_registries(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    return agent_registry, capability_registry


def test_explanation_accounts_for_full_score_weight(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["qa.acceptance_validation", "qa.traceability_check"],
        classification="internal",
    )
    result = match(request, agent_registry, capability_registry)
    explanation = explain_match_json(result)

    breakdown = explanation["primary"]["score_breakdown"]
    assert abs(sum(breakdown.values()) - explanation["primary"]["score"]) < 1e-9


def test_explanation_lists_every_rejected_candidate_with_reason(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["qa.acceptance_validation", "qa.traceability_check"],
        classification="internal",
    )
    result = match(request, agent_registry, capability_registry)
    explanation = explain_match_json(result)

    rejected_ids = {r["agent_id"] for r in explanation["rejected"]}
    assert "security_architect" in rejected_ids
    assert "architecture_writer" in rejected_ids
    for rejection in explanation["rejected"]:
        assert rejection["reason"]  # non-empty failing hard filter


def test_markdown_explanation_contains_primary_agent(loaded_registries):
    agent_registry, capability_registry = loaded_registries
    request = MatchRequest(
        explicit_capabilities=["qa.acceptance_validation", "qa.traceability_check"],
        classification="internal",
    )
    result = match(request, agent_registry, capability_registry)
    markdown = explain_match_markdown(result)

    assert "qa_evaluator" in markdown
    assert "Capability match explanation" in markdown
