"""Skill registry (masterplan section 7.1 registry layout).

Loads ``registry/skills/<skill_id>/skill.yaml``.
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.registries.base import RegistryError, load_yaml, validate_entry
from agent_platform.registries.models import SkillEntry
from agent_platform.schemas.okf_linter import SchemaRegistry


class SkillRegistry:
    def __init__(self, entries: dict[str, SkillEntry]):
        self.entries = entries

    def get(self, skill_id: str) -> SkillEntry | None:
        return self.entries.get(skill_id)

    def __len__(self) -> int:
        return len(self.entries)


def load_skill_registry(registry_dir: Path, schema_registry: SchemaRegistry) -> SkillRegistry:
    skills_dir = Path(registry_dir) / "skills"
    errors: list[str] = []
    entries: dict[str, SkillEntry] = {}

    if not skills_dir.exists():
        return SkillRegistry(entries={})

    for skill_dir in sorted(p for p in skills_dir.glob("*") if p.is_dir()):
        skill_yaml = skill_dir / "skill.yaml"
        if not skill_yaml.exists():
            errors.append(f"{skill_dir}: missing skill.yaml")
            continue
        raw = load_yaml(skill_yaml)
        entry_errors = validate_entry(raw, schema_registry, "skill.schema.json", context=str(skill_yaml))
        if entry_errors:
            errors.extend(entry_errors)
            continue
        entry = SkillEntry.model_validate(raw)
        if entry.skill_id in entries:
            errors.append(f"{skill_yaml}: duplicate skill_id '{entry.skill_id}'")
        else:
            entries[entry.skill_id] = entry

    if errors:
        raise RegistryError(errors)

    return SkillRegistry(entries=entries)
