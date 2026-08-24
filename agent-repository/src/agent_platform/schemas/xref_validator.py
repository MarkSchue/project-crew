"""Cross-reference validation for OKF relations.

Masterplan section 9.3 defines a controlled relation vocabulary; plan
section 23.1 requires that relations resolve through a stable ID index
rather than by mutable file path, and that the target's declared type is
compatible with the relation type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent_platform.schemas.canonicalize import OkfDocument, load_okf_file
from agent_platform.schemas.okf_linter import iter_okf_files

# Relation type -> allowed target OKF types. `None` means no restriction.
RELATION_TARGET_TYPES: dict[str, set[str] | None] = {
    "depends_on": None,
    "blocks": None,
    "implements": None,
    "satisfies": None,
    "derived_from": None,
    "supersedes": None,
    "contradicts": None,
    "validates": {"requirement", "user_story", "spoc"},
    "produces": {"test_result", "deliverable"},
    "consumes": None,
    "owned_by": None,
    "related_to": None,
    "generated_by": {"run_summary", "spoc"},
    "evidenced_by": {"run_summary", "test_result"},
    "reports_on": None,
    "part_of": {"epic"},
    "tested_by": {"test_case"},
}

DANGLING_REFERENCE = "OKF-XREF-001"
INCOMPATIBLE_RELATION_TYPE = "OKF-XREF-002"


@dataclass(frozen=True)
class XrefIssue:
    code: str
    message: str
    path: Path
    severity: str = "error"


@dataclass
class XrefResult:
    issues: list[XrefIssue] = field(default_factory=list)
    index: dict[str, OkfDocument] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


def build_id_index(root: Path) -> dict[str, OkfDocument]:
    """Load every OKF file under ``root`` and index it by its declared `id`.

    Files that fail to parse are silently skipped here; okf_linter reports
    parse errors separately.
    """
    index: dict[str, OkfDocument] = {}
    for path in iter_okf_files(root):
        try:
            document = load_okf_file(path)
        except Exception:  # noqa: BLE001 - handled by okf_linter
            continue
        doc_id = document.id
        if doc_id:
            index[doc_id] = document
    return index


def validate_cross_references(root: Path) -> XrefResult:
    """Validate that every `relations[].target` resolves to a known ID and
    that the relation type is compatible with the target's declared type."""
    index = build_id_index(root)
    result = XrefResult(index=index)

    for path in iter_okf_files(root):
        try:
            document = load_okf_file(path)
        except Exception:  # noqa: BLE001 - handled by okf_linter
            continue

        for relation in document.front_matter.get("relations") or []:
            if not isinstance(relation, dict):
                continue
            rel_type = relation.get("type")
            target_id = relation.get("target")
            if not target_id:
                continue

            target_doc = index.get(target_id)
            if target_doc is None:
                result.issues.append(
                    XrefIssue(
                        code=DANGLING_REFERENCE,
                        message=f"relation '{rel_type}' targets unknown id '{target_id}'",
                        path=document.path,
                    )
                )
                continue

            allowed_types = RELATION_TARGET_TYPES.get(rel_type)
            if allowed_types is not None and target_doc.type not in allowed_types:
                result.issues.append(
                    XrefIssue(
                        code=INCOMPATIBLE_RELATION_TYPE,
                        message=(
                            f"relation '{rel_type}' targets '{target_id}' of type "
                            f"'{target_doc.type}', expected one of {sorted(allowed_types)}"
                        ),
                        path=document.path,
                    )
                )

    return result
