from pathlib import Path

import pytest

from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.base import RegistryError
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.health import evaluate_health
from agent_platform.registries.model_registry import load_model_registry
from agent_platform.registries.skill_registry import load_skill_registry
from agent_platform.registries.tool_registry import load_tool_registry
from agent_platform.registries.validators import (
    check_activation_readiness,
    check_capability_evidence,
    check_deprecation_metadata,
    check_semantic_version,
)
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def registry_dir(fixtures_dir) -> Path:
    return fixtures_dir / "registry"


def test_capability_registry_loads_and_resolves_aliases(schema_dir, registry_dir):
    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)

    assert len(capability_registry.entries) >= 10
    assert "security.oauth2.design" in capability_registry
    assert capability_registry.resolve("oauth_design") == "security.oauth2.design"


def test_capability_registry_expands_dependencies(schema_dir, registry_dir):
    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)

    expanded = capability_registry.expand_dependencies({"security.oauth2.design"})
    assert "architecture.requirement_traceability" in expanded


def test_agent_registry_loads_all_agents(schema_dir, registry_dir):
    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)

    assert len(agent_registry) == 4
    assert agent_registry.get("security_architect") is not None
    assert agent_registry.get("qa_evaluator") is not None
    assert agent_registry.get("project_manager_agent") is not None


def test_agent_registry_rejects_dangling_capability_reference(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    broken_dir = fixtures_dir / "registry_invalid_dangling_capability"
    capability_registry = load_capability_registry(broken_dir, schema_registry)

    with pytest.raises(RegistryError) as exc_info:
        load_agent_registry(broken_dir, schema_registry, capability_registry)

    assert any("unknown capability" in e for e in exc_info.value.errors)


def test_skill_tool_model_workflow_registries_load(schema_dir, registry_dir):
    schema_registry = SchemaRegistry(schema_dir)
    skills = load_skill_registry(registry_dir, schema_registry)
    tools = load_tool_registry(registry_dir, schema_registry)
    models = load_model_registry(registry_dir, schema_registry)
    workflows = load_workflow_registry(registry_dir, schema_registry)

    assert len(skills) == 2
    assert len(tools) == 7
    assert len(models) == 2
    assert len(workflows) == 1
    assert workflows.get("requirement_to_delivery", "1.2.0") is not None


def test_check_capability_evidence_flags_missing_evidence(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    no_evidence_dir = fixtures_dir / "registry_no_evidence"
    capability_registry = load_capability_registry(no_evidence_dir, schema_registry)
    agent_registry = load_agent_registry(no_evidence_dir, schema_registry, capability_registry)

    agent = agent_registry.get("no_evidence_agent")
    errors = check_capability_evidence(agent)
    assert errors
    assert "no_evidence_agent" in errors[0]


def test_check_semantic_version():
    assert check_semantic_version("1.2.3", context="x") == []
    assert check_semantic_version("1.2", context="x") != []


def test_check_deprecation_metadata():
    assert check_deprecation_metadata("active", None, context="x") == []
    assert check_deprecation_metadata("deprecated", "new-id", context="x") == []
    assert check_deprecation_metadata("deprecated", None, context="x") != []
    assert check_deprecation_metadata("active", "new-id", context="x") != []


def test_check_activation_readiness_blocks_scaffolded_agent(schema_dir, registry_dir):
    from agent_platform.registries.models import AgentDefinition

    draft_agent = AgentDefinition.model_validate(
        {
            "schema_version": "agent/1.1",
            "agent_id": "new_agent",
            "version": "0.1.0",
            "name": "New Agent",
            "status": "draft",
            "role": "TODO: define this agent's role in one sentence.",
            "goal": "TODO: define this agent's goal in one sentence.",
            "capabilities": [],
            "health": {},
        }
    )
    errors = check_activation_readiness(draft_agent)
    assert errors  # not ready for activation


def test_evaluate_health_reports_unhealthy_without_removing(schema_dir, registry_dir):
    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)

    agent = agent_registry.get("qa_evaluator")
    status = evaluate_health(agent, observed_pass_rate=0.5)  # below minimum_pass_rate 0.95
    assert status.healthy is False
    # The agent is still present in the registry (not removed).
    assert agent_registry.get("qa_evaluator") is not None
