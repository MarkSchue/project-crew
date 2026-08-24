"""Shared loading and validation helpers for the Phase 2 registries.

Masterplan section 11.2 requirements: semantic versioning, deprecation
metadata, evaluation evidence for claimed capabilities, explicit data
classification limits, tool/model allowlists, owner/review metadata,
runtime health separate from static definition, no secrets in registry
files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from agent_platform.schemas.okf_linter import SchemaRegistry


class RegistryError(ValueError):
    """Raised when one or more registry entries fail schema validation.

    Carries every individual error so callers can report all problems at
    once instead of failing on the first one (masterplan M2.1 DoD: "fails
    loudly with a specific error").
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def validate_entry(
    entry: dict,
    schema_registry: SchemaRegistry,
    schema_filename: str,
    *,
    context: str,
) -> list[str]:
    """Validate one registry entry (a plain dict, no OKF front matter)
    against the named JSON Schema file. Returns a list of human-readable
    error strings (empty if valid)."""
    validator = schema_registry.validator_for_filename(schema_filename)
    errors = []
    for error in sorted(validator.iter_errors(entry), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in error.path) or "<root>"
        errors.append(f"{context}: {location}: {error.message}")
    return errors


def iter_yaml_files(directory: Path, pattern: str) -> Iterable[Path]:
    return sorted(Path(directory).glob(pattern))
