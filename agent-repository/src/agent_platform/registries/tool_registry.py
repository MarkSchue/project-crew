"""Tool registry (masterplan section 14.1).

Loads ``registry/tools/<tool_id>/tool.yaml``.
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.registries.base import RegistryError, load_yaml, validate_entry
from agent_platform.registries.models import ToolEntry
from agent_platform.schemas.okf_linter import SchemaRegistry


class ToolRegistry:
    def __init__(self, entries: dict[str, ToolEntry]):
        self.entries = entries

    def get(self, tool_id: str) -> ToolEntry | None:
        return self.entries.get(tool_id)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self.entries

    def __len__(self) -> int:
        return len(self.entries)


def load_tool_registry(registry_dir: Path, schema_registry: SchemaRegistry) -> ToolRegistry:
    tools_dir = Path(registry_dir) / "tools"
    errors: list[str] = []
    entries: dict[str, ToolEntry] = {}

    if not tools_dir.exists():
        return ToolRegistry(entries={})

    for tool_dir in sorted(p for p in tools_dir.glob("*") if p.is_dir()):
        tool_yaml = tool_dir / "tool.yaml"
        if not tool_yaml.exists():
            errors.append(f"{tool_dir}: missing tool.yaml")
            continue
        raw = load_yaml(tool_yaml)
        entry_errors = validate_entry(raw, schema_registry, "tool.schema.json", context=str(tool_yaml))
        if entry_errors:
            errors.extend(entry_errors)
            continue
        entry = ToolEntry.model_validate(raw)
        if entry.tool_id in entries:
            errors.append(f"{tool_yaml}: duplicate tool_id '{entry.tool_id}'")
        else:
            entries[entry.tool_id] = entry

    if errors:
        raise RegistryError(errors)

    return ToolRegistry(entries=entries)
