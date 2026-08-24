"""Agent registry (masterplan section 11.1-11.2).

Loads ``registry/agents/<agent_id>/agent.yaml``. Validates that every
claimed capability id resolves in the capability registry (masterplan
M2.1 DoD: "Loading a registry with a dangling capability reference ...
fails loudly with a specific error").
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.registries.base import RegistryError, load_yaml, validate_entry
from agent_platform.registries.capability_registry import CapabilityRegistry
from agent_platform.registries.models import AgentDefinition
from agent_platform.schemas.okf_linter import SchemaRegistry


class AgentRegistry:
    def __init__(self, entries: dict[str, AgentDefinition]):
        self.entries = entries

    def __getitem__(self, agent_id: str) -> AgentDefinition:
        return self.entries[agent_id]

    def __iter__(self):
        return iter(self.entries.values())

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, agent_id: str) -> AgentDefinition | None:
        return self.entries.get(agent_id)


def load_agent_registry(
    registry_dir: Path,
    schema_registry: SchemaRegistry,
    capability_registry: CapabilityRegistry,
) -> AgentRegistry:
    agents_dir = Path(registry_dir) / "agents"
    errors: list[str] = []
    entries: dict[str, AgentDefinition] = {}

    for agent_dir in sorted(p for p in agents_dir.glob("*") if p.is_dir()):
        agent_yaml = agent_dir / "agent.yaml"
        if not agent_yaml.exists():
            errors.append(f"{agent_dir}: missing agent.yaml")
            continue

        raw = load_yaml(agent_yaml)
        entry_errors = validate_entry(raw, schema_registry, "agent.schema.json", context=str(agent_yaml))
        if entry_errors:
            errors.extend(entry_errors)
            continue

        agent = AgentDefinition.model_validate(raw)

        for claim in agent.capabilities:
            if claim.id not in capability_registry:
                errors.append(
                    f"{agent_yaml}: agent '{agent.agent_id}' claims unknown capability '{claim.id}'"
                )

        if agent.agent_id in entries:
            errors.append(f"{agent_yaml}: duplicate agent_id '{agent.agent_id}'")
        else:
            entries[agent.agent_id] = agent

    if errors:
        raise RegistryError(errors)

    return AgentRegistry(entries=entries)
