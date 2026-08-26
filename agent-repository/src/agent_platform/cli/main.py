"""`mas` CLI (plan milestones M1.8, M1.9, M2.5).

Implements:

    mas project init <path> [--template <version>]
    mas project validate <path> [--schemas <dir>] [--mode fast|full]
    mas project migrate <path>
    mas index rebuild <path>
    mas registry validate <registry-dir> [--schemas <dir>]
    mas agent scaffold <agent-id> [--registry <registry-dir>]
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.persistence import InMemoryEventLedger
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.cli.agent_scaffold import scaffold_agent
from agent_platform.execution_plane.pm_query_flow import PmQueryFlow
from agent_platform.knowledge_graph.graph_generator import (
    GraphGenerationError,
    load_style_config,
    write_graph_index,
)
from agent_platform.migrations.runner import run_pending_migrations
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.base import RegistryError
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.model_registry import load_model_registry
from agent_platform.registries.skill_registry import load_skill_registry
from agent_platform.registries.tool_registry import load_tool_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.index_generator import rebuild_indexes
from agent_platform.schemas.okf_linter import SchemaRegistry, lint_directory
from agent_platform.schemas.xref_validator import validate_cross_references

app = typer.Typer(add_completion=False, help="Agent platform control-plane CLI.")
project_app = typer.Typer(add_completion=False, help="Project-level commands.")
index_app = typer.Typer(add_completion=False, help="Generated-index commands.")
graph_app = typer.Typer(add_completion=False, help="Knowledge-graph commands.")
registry_app = typer.Typer(add_completion=False, help="Registry commands.")
agent_app = typer.Typer(add_completion=False, help="Agent commands.")
app.add_typer(project_app, name="project")
app.add_typer(index_app, name="index")
app.add_typer(graph_app, name="graph")
app.add_typer(registry_app, name="registry")
app.add_typer(agent_app, name="agent")

console = Console()

_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_SCHEMA_DIR = _WORKSPACE_ROOT / "project-template-repository" / "schemas"
_DEFAULT_TEMPLATE_DIR = _WORKSPACE_ROOT / "project-template-repository" / "project_skeleton"
_DEFAULT_STYLE_CONFIG = Path(__file__).resolve().parents[1] / "knowledge_graph" / "style_config.yaml"


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


@project_app.command("init")
def project_init(
    path: Path = typer.Argument(..., help="Directory to create the new active project in."),
    template: str = typer.Option(
        "0.1.0", "--template", help="Template version to initialize from."
    ),
    template_dir: Path = typer.Option(
        _DEFAULT_TEMPLATE_DIR, "--template-dir", help="Path to the project_skeleton template directory."
    ),
) -> None:
    """Generate a new active-project repository from the pinned template
    (plan milestone M1.8). Writes a template.lock recording the exact
    template version and content hash."""
    if not template_dir.exists():
        console.print(f"[red]Template directory does not exist:[/red] {template_dir}")
        raise typer.Exit(code=2)
    if Path(path).exists() and any(Path(path).iterdir()):
        console.print(f"[red]Target directory is not empty:[/red] {path}")
        raise typer.Exit(code=2)

    shutil.copytree(template_dir, path)
    content_hash = _hash_directory(template_dir)
    lock_path = Path(path) / "template.lock"
    lock_path.write_text(
        f"template_version: \"{template}\"\n"
        f"template_content_hash: \"sha256:{content_hash}\"\n"
        f"generated_at: \"2026-08-24T09:00:00Z\"\n",
        encoding="utf-8",
    )
    console.print(f"[green]initialized[/green] {path} from template {template}")
    console.print(f"[green]template.lock[/green] content hash sha256:{content_hash}")


@project_app.command("migrate")
def project_migrate(
    path: Path = typer.Argument(..., help="Project directory to migrate."),
) -> None:
    """Apply pending project migrations (plan milestone M1.7/M1.9)."""
    if not Path(path).exists():
        console.print(f"[red]Path does not exist:[/red] {path}")
        raise typer.Exit(code=2)
    newly_applied = run_pending_migrations(path)
    if newly_applied:
        for migration in newly_applied:
            console.print(f"[green]applied[/green] {migration}")
    else:
        console.print("[green]no pending migrations[/green]")


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


@graph_app.command("rebuild")
def graph_rebuild(
    path: Path = typer.Argument(..., help="Project tree to generate graph_index.json for."),
    style_config: Path = typer.Option(
        _DEFAULT_STYLE_CONFIG, "--style-config", help="Path to the style_config.yaml file."
    ),
) -> None:
    """Regenerate `public/knowledge/graph_index.json` from the OKF files
    under PATH (masterplan section 9.6). Fails on dangling relations or
    node types with no style entry."""
    if not path.exists():
        console.print(f"[red]Path does not exist:[/red] {path}")
        raise typer.Exit(code=2)
    if not style_config.exists():
        console.print(f"[red]Style config does not exist:[/red] {style_config}")
        raise typer.Exit(code=2)

    config = load_style_config(style_config)
    try:
        written = write_graph_index(path, config)
    except GraphGenerationError as exc:
        console.print(f"[red]graph generation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]wrote[/green] {written}")


@registry_app.command("validate")
def registry_validate(
    registry_dir: Path = typer.Argument(..., help="Path to a registry/ directory."),
    schemas: Path = typer.Option(
        _DEFAULT_SCHEMA_DIR, "--schemas", help="Directory containing *.schema.json files."
    ),
) -> None:
    """Load and validate every registry (capabilities, agents, skills,
    tools, models, workflows) under REGISTRY_DIR (plan M2.1-M2.2)."""
    if not registry_dir.exists():
        console.print(f"[red]Path does not exist:[/red] {registry_dir}")
        raise typer.Exit(code=2)

    schema_registry = SchemaRegistry(schemas)
    try:
        capability_registry = load_capability_registry(registry_dir, schema_registry)
        agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
        load_skill_registry(registry_dir, schema_registry)
        load_tool_registry(registry_dir, schema_registry)
        load_model_registry(registry_dir, schema_registry)
        load_workflow_registry(registry_dir, schema_registry)
    except RegistryError as exc:
        table = Table(title="mas registry validate")
        table.add_column("error")
        for error in exc.errors:
            table.add_row(error)
        console.print(table)
        raise typer.Exit(code=1) from exc

    console.print(
        f"[green]OK[/green] {len(capability_registry.entries)} capabilities, "
        f"{len(agent_registry)} agents."
    )


@agent_app.command("scaffold")
def agent_scaffold_command(
    agent_id: str = typer.Argument(..., help="New agent id, e.g. security_architect."),
    registry_dir: Path = typer.Option(
        Path("registry"), "--registry", help="Path to the registry/ directory to scaffold into."
    ),
) -> None:
    """Generate a draft agent scaffold (masterplan section 11.3, plan M2.5)."""
    agent_dir = scaffold_agent(registry_dir, agent_id)
    console.print(f"[green]scaffolded[/green] {agent_dir} (status: draft)")


@app.command("chat")
def chat_command(
    question: str = typer.Option(None, "--question", help="One-shot question; omit for an interactive REPL."),
    project_root: Path = typer.Option(Path("."), "--project-root", help="Active project directory."),
    graph: Path = typer.Option(None, "--graph", help="Path to graph_index.json (regenerate with mas graph rebuild)."),
    classification: str = typer.Option("internal", "--classification", help="Session classification (public|internal)."),
) -> None:
    """Ask the standing Project Manager agent (read-only, masterplan 11.4)."""
    graph_index: dict | None = None
    if graph is not None:
        if not graph.exists():
            console.print(f"[red]Graph index not found:[/red] {graph}")
            raise typer.Exit(code=2)
        graph_index = json.loads(graph.read_text(encoding="utf-8"))

    flow = PmQueryFlow(
        policy=LocalDevPolicyDecisionPoint(decision_id_generator=SequentialIdGenerator()),
        graph_index=graph_index,
        project_root=project_root,
        event_ledger=InMemoryEventLedger(),
        id_generator=SequentialIdGenerator(),
        clock=FixedClock(),
    )
    session = flow.create_session(
        session_id=f"cli-{classification}", project_id="cli", classification=classification
    )

    def _answer(text: str) -> None:
        result = flow.ask(session.session_id, text)
        console.print(f"[bold]PM agent:[/bold] {result.answer}")
        if result.citations:
            console.print(f"[dim]citations:[/dim] {', '.join(result.citations)}")

    if question:
        _answer(question)
        return

    console.print("Ask the Project Manager agent (read-only). Type 'quit' to exit.")
    while True:
        line = typer.prompt(">")
        if line.strip().lower() in {"quit", "exit", "q"}:
            break
        _answer(line)


def _hash_directory(directory: Path) -> str:
    """Deterministic content hash of a template directory: sha256 over a
    sorted list of (relative path, file sha256) pairs."""
    file_hashes = []
    for path in sorted(Path(directory).rglob("*")):
        if not path.is_file():
            continue
        file_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = path.relative_to(directory).as_posix()
        file_hashes.append(f"{rel}:{file_digest}")
    combined = "\n".join(file_hashes)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    app()
