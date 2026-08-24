from pathlib import Path

import pytest

from agent_platform.cli.agent_scaffold import scaffold_agent
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.validators import check_activation_readiness
from agent_platform.schemas.okf_linter import SchemaRegistry


def test_scaffold_agent_produces_schema_valid_draft(tmp_path, schema_dir, fixtures_dir):
    registry_dir = tmp_path / "registry"
    (registry_dir / "capabilities").mkdir(parents=True)
    (registry_dir / "capabilities" / "capability_catalog.yaml").write_text(
        "capabilities: []\n", encoding="utf-8"
    )

    agent_dir = scaffold_agent(registry_dir, "new_agent")

    assert (agent_dir / "agent.yaml").exists()
    assert (agent_dir / "prompt.md").exists()
    assert (agent_dir / "tests" / "evaluation_fixture.yaml").exists()
    assert (agent_dir / "private_knowledge" / "index.md").exists()

    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)

    agent = agent_registry.get("new_agent")
    assert agent is not None
    assert agent.status == "draft"


def test_scaffolded_agent_fails_activation_readiness(tmp_path, schema_dir):
    registry_dir = tmp_path / "registry"
    (registry_dir / "capabilities").mkdir(parents=True)
    (registry_dir / "capabilities" / "capability_catalog.yaml").write_text(
        "capabilities: []\n", encoding="utf-8"
    )

    scaffold_agent(registry_dir, "new_agent")

    schema_registry = SchemaRegistry(schema_dir)
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    agent = agent_registry.get("new_agent")

    errors = check_activation_readiness(agent)
    assert errors  # scaffolded agent is not ready for activation
