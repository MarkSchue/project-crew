"""`mas` CLI skeleton (plan milestone M1.8).

Implements the subset needed to exercise the Phase 0/1 foundation:

    mas project validate <path> [--schemas <dir>] [--mode fast|full]
    mas index rebuild <path>
    mas registry validate

`mas registry validate` is a stub until the Phase 2 registries land (plan
section 7 / M2.x); it reports that no registry exists yet rather than
failing, per the original M1.8 scope.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agent_platform.schemas.index_generator import rebuild_indexes
from agent_platform.schemas.okf_linter import SchemaRegistry, lint_directory
from agent_platform.schemas.xref_validator import validate_cross_references

app = typer.Typer(add_completion=False, help="Agent platform control-plane CLI.")
project_app = typer.Typer(add_completion=False, help="Project-level commands.")
index_app = typer.Typer(add_completion=False, help="Generated-index commands.")
registry_app = typer.Typer(add_completion=False, help="Registry commands.")
app.add_typer(project_app, name="project")
app.add_typer(index_app, name="index")
app.add_typer(registry_app, name="registry")

console = Console()

_DEFAULT_SCHEMA_DIR = (
    Path(__file__).resolve().parents[4] / "project-template-repository" / "schemas"
)


@project_app.command("validate")
def project_validate(
    path: Path = typer.Argument(..., help="Directory of OKF Markdown files to validate."),
    schemas: Path = typer.Option(
        _DEFAULT_SCHEMA_DIR, "--schemas", help="Directory containing *.schema.json files."
    ),
    mode: str = typer.Option("full", "--mode", help="fast (schema only) or full (schema + xref)."),
) -> None:
    """Run the OKF linter (and, in full mode, the cross-reference validator)
    against every OKF Markdown file under PATH."""
    if not path.exists():
        console.print(f"[red]Path does not exist:[/red] {path}")
        raise typer.Exit(code=2)

    registry = SchemaRegistry(schemas)
    lint_result = lint_directory(path, registry)

    table = Table(title="mas project validate")
    table.add_column("severity")
    table.add_column("code")
    table.add_column("path")
    table.add_column("message")

    for issue in lint_result.issues:
        table.add_row(issue.severity, issue.code, str(issue.path), issue.message)

    xref_ok = True
    if mode == "full":
        xref_result = validate_cross_references(path)
        xref_ok = xref_result.ok
        for issue in xref_result.issues:
            table.add_row(issue.severity, issue.code, str(issue.path), issue.message)

    if table.row_count:
        console.print(table)
    else:
        console.print("[green]No issues found.[/green]")

    if not lint_result.ok or not xref_ok:
        raise typer.Exit(code=1)


@index_app.command("rebuild")
def index_rebuild(
    path: Path = typer.Argument(..., help="Directory tree to regenerate index.md files for."),
) -> None:
    """Regenerate `index.md` for every directory under PATH that contains
    OKF Markdown files."""
    if not path.exists():
        console.print(f"[red]Path does not exist:[/red] {path}")
        raise typer.Exit(code=2)
    written = rebuild_indexes(path)
    for index_path in written:
        console.print(f"[green]wrote[/green] {index_path}")
    console.print(f"Regenerated {len(written)} index file(s).")


@registry_app.command("validate")
def registry_validate() -> None:
    """Stub until Phase 2 registries (agent/capability/skill/tool/model) are
    implemented; see plan milestones M2.1-M2.2."""
    console.print("[yellow]no registry implemented yet (Phase 2 pending)[/yellow]")


if __name__ == "__main__":
    app()
