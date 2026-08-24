"""Model catalog registry.

Loads ``registry/models/model_catalog.yaml`` (a list of model-profile
entries).
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.registries.base import RegistryError, load_yaml, validate_entry
from agent_platform.registries.models import ModelCatalogEntry
from agent_platform.schemas.okf_linter import SchemaRegistry

CATALOG_FILENAME = "model_catalog.yaml"


class ModelRegistry:
    def __init__(self, entries: dict[str, ModelCatalogEntry]):
        self.entries = entries

    def get(self, profile_id: str) -> ModelCatalogEntry | None:
        return self.entries.get(profile_id)

    def __len__(self) -> int:
        return len(self.entries)


def load_model_registry(registry_dir: Path, schema_registry: SchemaRegistry) -> ModelRegistry:
    models_dir = Path(registry_dir) / "models"
    catalog_path = models_dir / CATALOG_FILENAME
    if not catalog_path.exists():
        return ModelRegistry(entries={})

    raw = load_yaml(catalog_path) or []
    raw_entries = raw.get("profiles", raw) if isinstance(raw, dict) else raw
    if not isinstance(raw_entries, list):
        raise RegistryError([f"{catalog_path}: expected a list of model profile entries"])

    errors: list[str] = []
    entries: dict[str, ModelCatalogEntry] = {}
    for raw_entry in raw_entries:
        entry_errors = validate_entry(
            raw_entry, schema_registry, "model_catalog.schema.json", context=str(catalog_path)
        )
        if entry_errors:
            errors.extend(entry_errors)
            continue
        entry = ModelCatalogEntry.model_validate(raw_entry)
        if entry.profile_id in entries:
            errors.append(f"{catalog_path}: duplicate profile_id '{entry.profile_id}'")
        else:
            entries[entry.profile_id] = entry

    if errors:
        raise RegistryError(errors)

    return ModelRegistry(entries=entries)
