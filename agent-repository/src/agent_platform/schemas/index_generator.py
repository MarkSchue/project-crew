"""Generates per-directory `index.md` projections from OKF front matter.

Masterplan section 9.4: "Each directory has an `index.md` generated from
front matter. The index is treated as a projection and can be regenerated."
Indexes are pure projections: running the generator twice on an unchanged
tree must produce a byte-identical result (plan milestone M1.6).
"""

from __future__ import annotations

from pathlib import Path

from agent_platform.schemas.canonicalize import load_okf_file

GENERATED_MARKER = (
    "<!-- GENERATED FILE. Do not edit by hand; regenerate with `mas index rebuild`. -->"
)


def _row(doc) -> tuple[str, str, str, str, str]:
    fm = doc.front_matter
    return (
        str(fm.get("id", "")),
        str(fm.get("type", "")),
        str(fm.get("status", "")),
        str(fm.get("title", "")),
        doc.path.name,
    )


def render_index(directory: Path, entries: list[tuple[str, str, str, str, str]]) -> str:
    lines = [
        GENERATED_MARKER,
        "",
        f"# Index of `{directory.name}/`",
        "",
        "| id | type | status | title | file |",
        "|---|---|---|---|---|",
    ]
    for doc_id, doc_type, status, title, filename in entries:
        lines.append(f"| {doc_id} | {doc_type} | {status} | {title} | [{filename}](./{filename}) |")
    lines.append("")
    return "\n".join(lines)


def generate_index_for_directory(directory: Path) -> str | None:
    """Return the generated index.md content for one directory, or None if
    the directory contains no OKF Markdown files."""
    md_files = sorted(
        p for p in Path(directory).glob("*.md") if p.name not in {"index.md", "README.md"}
    )
    entries = []
    for path in md_files:
        try:
            doc = load_okf_file(path)
        except Exception:  # noqa: BLE001 - skip unparsable files; okf_linter reports them
            continue
        entries.append(_row(doc))

    if not entries:
        return None

    entries.sort(key=lambda row: row[0])
    return render_index(Path(directory), entries)


def rebuild_indexes(root: Path) -> list[Path]:
    """Regenerate `index.md` for every directory under root (including root
    itself) that contains at least one OKF Markdown file. Returns the list
    of index.md paths written."""
    written: list[Path] = []
    root = Path(root)
    directories = [root] + [p for p in sorted(root.rglob("*")) if p.is_dir()]

    for directory in directories:
        content = generate_index_for_directory(directory)
        if content is None:
            continue
        index_path = directory / "index.md"
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else None
        if existing != content:
            index_path.write_text(content, encoding="utf-8")
        written.append(index_path)

    return written
