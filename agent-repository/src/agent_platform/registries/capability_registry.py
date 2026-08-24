"""Capability catalog registry (masterplan section 11.2, 12.1).

Loads ``registry/capabilities/capability_catalog.yaml`` (a list of
capability entries) and the optional ``capability_aliases.yaml`` alias map.
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.registries.base import RegistryError, load_yaml, validate_entry
from agent_platform.registries.models import CapabilityEntry
from agent_platform.schemas.okf_linter import SchemaRegistry

CATALOG_FILENAME = "capability_catalog.yaml"
ALIASES_FILENAME = "capability_aliases.yaml"


class CapabilityRegistry:
    def __init__(self, entries: dict[str, CapabilityEntry], aliases: dict[str, str]):
        self.entries = entries
        self.aliases = aliases

    def resolve(self, capability_id: str) -> str:
        """Resolve an alias to its canonical capability id (identity if not
        an alias)."""
        return self.aliases.get(capability_id, capability_id)

    def get(self, capability_id: str) -> CapabilityEntry | None:
        return self.entries.get(self.resolve(capability_id))

    def __contains__(self, capability_id: str) -> bool:
        return self.resolve(capability_id) in self.entries

    def expand_dependencies(self, capability_ids: set[str]) -> set[str]:
        """Expand a set of capability ids to include everything they
        transitively `requires` (masterplan section 3.3 stage 2)."""
        resolved = {self.resolve(cid) for cid in capability_ids}
        frontier = set(resolved)
        while frontier:
            next_frontier: set[str] = set()
            for cid in frontier:
                entry = self.entries.get(cid)
                if not entry:
                    continue
                for dep in entry.requires:
                    dep_resolved = self.resolve(dep)
                    if dep_resolved not in resolved:
                        resolved.add(dep_resolved)
                        next_frontier.add(dep_resolved)
            frontier = next_frontier
        return resolved


def load_capability_registry(registry_dir: Path, schema_registry: SchemaRegistry) -> CapabilityRegistry:
    capabilities_dir = Path(registry_dir) / "capabilities"
    catalog_path = capabilities_dir / CATALOG_FILENAME
    if not catalog_path.exists():
        raise RegistryError([f"missing capability catalog: {catalog_path}"])

    raw = load_yaml(catalog_path) or []
    raw_entries = raw.get("capabilities", raw) if isinstance(raw, dict) else raw
    if not isinstance(raw_entries, list):
        raise RegistryError([f"{catalog_path}: expected a list of capability entries"])

    errors: list[str] = []
    entries: dict[str, CapabilityEntry] = {}
    for raw_entry in raw_entries:
        errors.extend(
            validate_entry(raw_entry, schema_registry, "capability.schema.json", context=str(catalog_path))
        )
        if not errors:
            entry = CapabilityEntry.model_validate(raw_entry)
            if entry.id in entries:
                errors.append(f"{catalog_path}: duplicate capability id '{entry.id}'")
            else:
                entries[entry.id] = entry

    if errors:
        raise RegistryError(errors)

    aliases_path = capabilities_dir / ALIASES_FILENAME
    aliases: dict[str, str] = {}
    if aliases_path.exists():
        raw_aliases = load_yaml(aliases_path) or {}
        if not isinstance(raw_aliases, dict):
            raise RegistryError([f"{aliases_path}: expected a mapping of alias -> canonical id"])
        aliases = dict(raw_aliases)

    # Also fold each entry's own `aliases` list into the alias map.
    for entry in entries.values():
        for alias in entry.aliases:
            aliases.setdefault(alias, entry.id)

    return CapabilityRegistry(entries=entries, aliases=aliases)
