"""Workflow registry (plan section 19.4, ADR-015).

Loads ``registry/workflows/<workflow_id>/<version>.yaml``, one file per
workflow version (the corrected layout from ADR-015, superseding the
masterplan's single ``workflow_catalog.yaml``).
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.registries.base import RegistryError, load_yaml, validate_entry
from agent_platform.registries.models import WorkflowCatalogEntry
from agent_platform.schemas.okf_linter import SchemaRegistry


class WorkflowRegistry:
    def __init__(self, entries: dict[tuple[str, str], WorkflowCatalogEntry]):
        self.entries = entries

    def get(self, workflow_id: str, version: str) -> WorkflowCatalogEntry | None:
        return self.entries.get((workflow_id, version))

    def __len__(self) -> int:
        return len(self.entries)


def load_workflow_registry(registry_dir: Path, schema_registry: SchemaRegistry) -> WorkflowRegistry:
    workflows_dir = Path(registry_dir) / "workflows"
    errors: list[str] = []
    entries: dict[tuple[str, str], WorkflowCatalogEntry] = {}

    if not workflows_dir.exists():
        return WorkflowRegistry(entries={})

    for workflow_dir in sorted(p for p in workflows_dir.glob("*") if p.is_dir()):
        for version_file in sorted(workflow_dir.glob("*.yaml")):
            raw = load_yaml(version_file)
            entry_errors = validate_entry(
                raw, schema_registry, "workflow_catalog.schema.json", context=str(version_file)
            )
            if entry_errors:
                errors.extend(entry_errors)
                continue
            entry = WorkflowCatalogEntry.model_validate(raw)
            key = (entry.workflow_id, entry.version)
            if key in entries:
                errors.append(f"{version_file}: duplicate workflow {key}")
            else:
                entries[key] = entry

    if errors:
        raise RegistryError(errors)

    return WorkflowRegistry(entries=entries)
