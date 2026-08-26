"""Documentation-as-code analyzer (plan section 17.8).

Implements the machine-checkable core of the documentation strategy
using Python AST analysis (never importing application code):

- **code-unit discovery** — walk ``src/``, parse with ``ast``, and treat
  every top-level class (including protocols and enums) and every
  non-private top-level function as a required, documentable code unit.
- **code-to-document mapping** — ``code_ref`` front matter
  (``src/.../file.py#Symbol``) links a document to a discovered unit.
- **document-to-code reverse mapping** — a document whose ``code_ref``
  resolves to nothing is orphaned (an error).
- **front-matter validation** — ``schema_version: code-doc/1.0``, required
  keys, stable ``doc_id`` uniqueness.
- **coverage** — ``documented_required_code_units /
  discovered_required_code_units``.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from agent_platform.schemas.canonicalize import load_okf_file

CODE_DOC_SCHEMA_VERSION = "code-doc/1.0"

_REQUIRED_FRONT_MATTER_KEYS = (
    "schema_version",
    "doc_id",
    "code_unit_id",
    "title",
    "code_ref",
    "unit_type",
    "status",
    "owner_role",
    "introduced_in",
    "classification",
    "related_requirements",
    "related_adrs",
    "related_test_cases",
    "last_verified_commit",
)

# Every code document must contain at least these sections.
_REQUIRED_SECTIONS = ("## Purpose",)


@dataclass(frozen=True)
class DiscoveredUnit:
    symbol: str
    file: str  # repo-relative posix path, e.g. src/agent_platform/domain/run.py
    kind: str  # class | protocol | enum | function
    ref: str   # src/.../file.py#Symbol

    @property
    def is_private(self) -> bool:
        return self.symbol.startswith("_")


@dataclass(frozen=True)
class CodeDoc:
    path: Path
    front_matter: dict
    doc_id: str
    code_ref: str
    file_part: str
    symbol: str | None

    @property
    def is_module_doc(self) -> bool:
        return self.symbol is None


@dataclass
class DocsReport:
    discovered_units: list[DiscoveredUnit] = field(default_factory=list)
    docs: list[CodeDoc] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    undocumented: list[str] = field(default_factory=list)

    @property
    def required_units(self) -> list[DiscoveredUnit]:
        return [u for u in self.discovered_units if not u.is_private]

    @property
    def documented_count(self) -> int:
        return len(self.required_units) - len(self.undocumented)

    @property
    def coverage_ratio(self) -> float:
        if not self.required_units:
            return 1.0
        return self.documented_count / len(self.required_units)

    @property
    def ok(self) -> bool:
        return not self.errors


def _class_kind(node: ast.ClassDef) -> str:
    for base in node.bases:
        if isinstance(base, ast.Name):
            if base.id == "Protocol":
                return "protocol"
            if base.id in ("Enum", "StrEnum", "IntEnum"):
                return "enum"
    return "class"


def discover_units(root: Path, repo_root: Path) -> list[DiscoveredUnit]:
    units: list[DiscoveredUnit] = []
    for py_path in sorted(Path(root).rglob("*.py")):
        if py_path.name == "__init__.py":
            continue
        rel = py_path.relative_to(repo_root).as_posix()
        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.ClassDef,)):
                units.append(
                    DiscoveredUnit(
                        symbol=node.name,
                        file=rel,
                        kind=_class_kind(node),
                        ref=f"{rel}#{node.name}",
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                units.append(
                    DiscoveredUnit(
                        symbol=node.name,
                        file=rel,
                        kind="function",
                        ref=f"{rel}#{node.name}",
                    )
                )
    units.sort(key=lambda u: (u.file, u.symbol))
    return units


def load_code_docs(docs_root: Path) -> list[CodeDoc]:
    docs: list[CodeDoc] = []
    implementation_root = Path(docs_root) / "implementation"
    if not implementation_root.exists():
        return docs
    for md_path in sorted(implementation_root.rglob("*.md")):
        try:
            document = load_okf_file(md_path)
        except Exception:  # noqa: BLE001 - reported by the linter separately
            continue
        fm = document.front_matter
        if fm.get("schema_version") != CODE_DOC_SCHEMA_VERSION:
            continue  # not a code-doc (e.g. a README or index)
        code_ref = str(fm.get("code_ref", ""))
        file_part, _, symbol = code_ref.partition("#")
        docs.append(
            CodeDoc(
                path=md_path,
                front_matter=fm,
                doc_id=str(fm.get("doc_id", "")),
                code_ref=code_ref,
                file_part=file_part,
                symbol=symbol or None,
            )
        )
    docs.sort(key=lambda d: d.path.as_posix())
    return docs


def _resolve_unit(units_by_ref: dict[str, DiscoveredUnit], code_ref: str) -> DiscoveredUnit | None:
    if code_ref in units_by_ref:
        return units_by_ref[code_ref]
    return None


def analyze(src_root: Path, docs_root: Path) -> DocsReport:
    report = DocsReport()

    repo_root = Path(src_root).parent.parent  # agent-repository
    units = discover_units(src_root, repo_root)
    tools_dir = repo_root / "tools"
    if tools_dir.is_dir():
        units += discover_units(tools_dir, repo_root)
    units.sort(key=lambda u: (u.file, u.symbol))
    report.discovered_units = units
    units_by_ref = {u.ref: u for u in units}

    docs = load_code_docs(docs_root)
    report.docs = docs

    doc_ids: dict[str, Path] = {}
    for doc in docs:
        # 1. front-matter completeness
        for key in _REQUIRED_FRONT_MATTER_KEYS:
            if key not in doc.front_matter:
                report.errors.append(f"{doc.path}: missing front-matter key '{key}'")
        # 2. stable doc_id uniqueness
        if not doc.doc_id:
            report.errors.append(f"{doc.path}: empty doc_id")
        elif doc.doc_id in doc_ids:
            report.errors.append(
                f"{doc.path}: duplicate doc_id '{doc.doc_id}' (first seen at {doc_ids[doc.doc_id]})"
            )
        else:
            doc_ids[doc.doc_id] = doc.path
        # 3. required sections present
        text = doc.path.read_text(encoding="utf-8")
        for section in _REQUIRED_SECTIONS:
            if section not in text:
                report.warnings.append(f"{doc.path}: missing required section '{section}'")

        # 4. module docs: code_ref must resolve to a file or directory
        if doc.is_module_doc:
            candidate = repo_root / doc.file_part if doc.file_part else None
            if doc.file_part and candidate is not None and not candidate.exists():
                report.errors.append(
                    f"{doc.path}: code_ref '{doc.code_ref}' does not resolve to a file or directory"
                )
            continue

        # 5. class docs: code_ref must resolve to a discovered unit
        if _resolve_unit(units_by_ref, doc.code_ref) is None:
            report.errors.append(
                f"{doc.path}: code_ref '{doc.code_ref}' does not resolve to a discovered code unit (orphaned document)"
            )

    # coverage: every required code unit needs a resolving document
    documented_refs = {doc.code_ref for doc in docs if not doc.is_module_doc}
    for unit in report.required_units:
        if unit.ref not in documented_refs:
            report.undocumented.append(unit.ref)

    return report
