"""Knowledge-graph generator (masterplan section 9.6, plan milestone
M9.1).

Walks all OKF files in the active project, builds nodes and edges from
``id``, ``type``, ``status``, ``owner``, ``relations``, ``source_refs``,
and ``cross_references``, and includes non-OKF leaf nodes (``events.jsonl``)
reachable through ``generated_by``/``evidenced_by`` edges. The output
``public/knowledge/graph_index.json`` is a regenerable projection, never
hand-edited, and is rebuilt by CI and by ``mas graph rebuild``.

Generator invariants:

- Idempotent: running twice on an unchanged tree writes byte-identical
  output (same rule as M1.6).
- Every node's ``type`` must resolve to a style-config entry; unknown
  types raise (fail CI rather than render unstyled).
- A relation whose target does not resolve to a known node id is a
  dangling relation and fails the build (masterplan section 9.6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import iter_okf_files

GRAPH_FILE_NAME = "graph_index.json"

# The relation types that may point at non-OKF evidence (events.jsonl) and
# are materialized as edges into raw_event leaf nodes when the target
# resolves to a leaf-node id.
_EVIDENCE_RELATION_TYPES = {"generated_by", "evidenced_by"}


class GraphGenerationError(ValueError):
    """Raised when the graph cannot be generated: unknown node type or a
    dangling relation."""


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    status: str
    owner: str
    title: str
    path: str
    classification: str
    source_refs: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "owner": self.owner,
            "title": self.title,
            "path": self.path,
            "classification": self.classification,
            "source_refs": list(self.source_refs),
            "cross_references": list(self.cross_references),
        }


@dataclass(frozen=True)
class GraphEdge:
    type: str
    source: str
    target: str

    def to_dict(self) -> dict:
        return {"type": self.type, "source": self.source, "target": self.target}


@dataclass
class GraphIndex:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    dangling_relations: list[str] = field(default_factory=list)
    unknown_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def render_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"


def load_style_config(path: Path) -> dict[str, dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {str(k): v for k, v in (data or {}).get("types", {}).items()}


def _raw_event_leaf_id(path: Path, root: Path) -> str:
    return f"raw:{path.relative_to(root).as_posix()}"


def _resolve_evidence_ref(
    source_path: Path,
    target: str,
    root: Path,
    raw_event_by_relpath: dict[str, str],
    raw_event_by_basename: dict[str, list[str]],
) -> str | None:
    """Resolve an ``evidenced_by``/``generated_by`` target that is a path
    (e.g. ``events.jsonl``) to a raw_event leaf-node id.

    Resolution order: relative to the source file's directory first; then,
    for a bare filename, a unique leaf with that basename."""
    candidate = (source_path.parent / target).resolve()
    try:
        rel = candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = None
    if rel is not None and rel in raw_event_by_relpath:
        return raw_event_by_relpath[rel]

    if "/" not in target and "\\" not in target:
        matches = raw_event_by_basename.get(target, [])
        if len(matches) == 1:
            return matches[0]
    return None


def _jsonl_files(root: Path) -> list[Path]:
    return sorted(p for p in Path(root).rglob("*.jsonl") if p.is_file())


def generate_graph_index(root: Path, style_config: dict[str, dict]) -> GraphIndex:
    root = Path(root)
    known_types = set(style_config)
    index = GraphIndex()
    nodes_by_id: dict[str, GraphNode] = {}
    node_path_by_id: dict[str, Path] = {}

    # 1. OKF nodes.
    for path in iter_okf_files(root):
        try:
            doc = load_okf_file(path)
        except Exception:  # noqa: BLE001 - unparsable files are the linter's concern
            continue
        doc_id = doc.id
        doc_type = doc.type
        if not doc_id:
            continue
        fm = doc.front_matter
        node = GraphNode(
            id=doc_id,
            type=str(doc_type or ""),
            status=str(fm.get("status", "")),
            owner=str(fm.get("owner", "")),
            title=str(fm.get("title", "")),
            path=str(path.relative_to(root).as_posix()),
            classification=str(fm.get("classification", "internal")),
            source_refs=[str(r) for r in (fm.get("source_refs") or [])],
            cross_references=[str(r) for r in (fm.get("cross_references") or [])],
        )
        if node.type not in known_types:
            index.unknown_types.append(node.type)
        nodes_by_id[node.id] = node
        node_path_by_id[node.id] = path
        index.nodes.append(node)

    # 2. Non-OKF leaf nodes (events.jsonl).
    raw_event_by_relpath: dict[str, str] = {}
    raw_event_by_basename: dict[str, list[str]] = {}
    for jsonl_path in _jsonl_files(root):
        leaf_id = _raw_event_leaf_id(jsonl_path, root)
        rel = jsonl_path.relative_to(root).as_posix()
        raw_event_by_relpath[rel] = leaf_id
        raw_event_by_basename.setdefault(jsonl_path.name, []).append(leaf_id)
        nodes_by_id[leaf_id] = GraphNode(
            id=leaf_id,
            type="raw_event",
            status="",
            owner="",
            title=jsonl_path.name,
            path=rel,
            classification="internal",
        )
        index.nodes.append(nodes_by_id[leaf_id])

    # 3. Edges from relations + source_refs (resolve-by-id, then resolve
    #    evidence references relative to the source file's directory).
    for path in iter_okf_files(root):
        try:
            doc = load_okf_file(path)
        except Exception:  # noqa: BLE001
            continue
        if not doc.id:
            continue
        for relation in doc.front_matter.get("relations") or []:
            if not isinstance(relation, dict):
                continue
            rel_type = str(relation.get("type", ""))
            target = relation.get("target")
            if not target:
                continue
            target_str = str(target)
            if target_str in nodes_by_id:
                index.edges.append(GraphEdge(type=rel_type, source=doc.id, target=target_str))
                continue
            if rel_type in _EVIDENCE_RELATION_TYPES:
                resolved = _resolve_evidence_ref(
                    path, target_str, root, raw_event_by_relpath, raw_event_by_basename
                )
                if resolved is not None:
                    index.edges.append(GraphEdge(type=rel_type, source=doc.id, target=resolved))
                    continue
            index.dangling_relations.append(
                f"{doc.id}: relation '{rel_type}' -> unknown id '{target_str}'"
            )

    index.nodes.sort(key=lambda n: n.id)
    index.edges.sort(key=lambda e: (e.type, e.source, e.target))
    index.dangling_relations.sort()
    index.unknown_types = sorted(set(index.unknown_types))
    return index


def build_and_validate(root: Path, style_config: dict[str, dict]) -> GraphIndex:
    """Generate the graph and enforce the generator invariants (unknown
    type or dangling relation raises)."""
    index = generate_graph_index(root, style_config)
    if index.unknown_types:
        raise GraphGenerationError(
            f"node types with no style entry: {', '.join(index.unknown_types)}"
        )
    if index.dangling_relations:
        raise GraphGenerationError(
            f"dangling relations: {', '.join(index.dangling_relations)}"
        )
    return index


def write_graph_index(
    root: Path,
    style_config: dict[str, dict],
    *,
    output_path: Path | None = None,
) -> Path:
    """Regenerate ``graph_index.json`` under ``root`` and return the path
    written. Idempotent: unchanged output is not rewritten."""
    index = build_and_validate(root, style_config)
    content = index.render_json()
    target = Path(output_path) if output_path else Path(root) / "public" / "knowledge" / GRAPH_FILE_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else None
    if existing != content:
        target.write_text(content, encoding="utf-8")
    return target
