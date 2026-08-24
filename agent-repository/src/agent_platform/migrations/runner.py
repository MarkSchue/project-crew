"""Migration discovery and application runner (plan milestone M1.7/M1.9).

Discovers ``NNNN_description.py`` modules in this package and applies
their ``up()`` functions in ascending numeric order to a target project
directory, skipping migrations already recorded in the project's
``.migration_state`` marker.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from pathlib import Path

_MIGRATION_NAME_RE = re.compile(r"^(?P<number>\d{4})_(?P<name>[a-z0-9_]+)\.py$")


@dataclass(frozen=True)
class Migration:
    number: int
    name: str
    module_path: str

    @property
    def key(self) -> str:
        return f"{self.number:04d}_{self.name}"


def discover_migrations() -> list[Migration]:
    package_dir = Path(__file__).resolve().parent
    migrations: list[Migration] = []
    for path in sorted(package_dir.glob("*.py")):
        match = _MIGRATION_NAME_RE.match(path.name)
        if not match:
            continue
        migrations.append(
            Migration(
                number=int(match.group("number")),
                name=match.group("name"),
                module_path=f"agent_platform.migrations.{path.stem}",
            )
        )
    return sorted(migrations, key=lambda m: m.number)


def applied_migrations(project_dir: Path) -> set[str]:
    marker = Path(project_dir) / ".migration_state"
    if not marker.exists():
        return set()
    return {line.strip() for line in marker.read_text(encoding="utf-8").splitlines() if line.strip()}


def run_pending_migrations(project_dir: Path) -> list[str]:
    """Apply every pending migration to `project_dir`. Returns the list of
    migration keys that were newly applied (empty if up to date)."""
    applied = applied_migrations(project_dir)
    newly_applied: list[str] = []
    for migration in discover_migrations():
        if migration.key in applied:
            continue
        module = importlib.import_module(migration.module_path)
        module.up(project_dir)
        newly_applied.append(migration.key)
    return newly_applied
