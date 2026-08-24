"""0001_initial — no-op baseline migration.

Marks the initial schema version so later migrations have a known
starting point (plan milestone M1.7). Applying it to a project writes a
`migration_state` marker recording that 0001 has been applied; no schema
change is performed.
"""

from __future__ import annotations

from pathlib import Path


def up(project_dir: Path) -> None:
    marker = Path(project_dir) / ".migration_state"
    marker.parent.mkdir(parents=True, exist_ok=True)
    applied = _load_applied(marker)
    if "0001_initial" not in applied:
        applied.append("0001_initial")
        marker.write_text("\n".join(sorted(applied)) + "\n", encoding="utf-8")


def down(project_dir: Path) -> None:
    marker = Path(project_dir) / ".migration_state"
    applied = _load_applied(marker)
    if "0001_initial" in applied:
        applied.remove("0001_initial")
        marker.write_text("\n".join(sorted(applied)) + "\n", encoding="utf-8")


def _load_applied(marker: Path) -> list[str]:
    if not marker.exists():
        return []
    return [line.strip() for line in marker.read_text(encoding="utf-8").splitlines() if line.strip()]
