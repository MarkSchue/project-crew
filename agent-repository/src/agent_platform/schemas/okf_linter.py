"""JSON Schema validation and OKF-specific lint rules.

Wraps the JSON Schemas in ``project-template-repository/schemas`` and adds
the coverage checks from masterplan section 9.7 that cannot be expressed as
plain JSON Schema (they need a specific, distinct lint code per finding).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import jsonschema
import referencing
import referencing.jsonschema

from agent_platform.schemas.canonicalize import OkfDocument, load_okf_file

# Lint codes -----------------------------------------------------------------
SCHEMA_ERROR = "OKF-SCHEMA-001"
DUPLICATE_ID = "OKF-ID-001"
UNTESTED_USER_STORY = "OKF-COVERAGE-001"
MISSING_TEST_CASE_REF = "OKF-COVERAGE-002"

# OKF types that resolve to a schema other than the generic OKF base schema.
_TYPE_SCHEMA_OVERRIDES = {"spoc": "spoc.schema.json"}

_MARKDOWN_EXCLUDE_NAMES = {"index.md", "README.md"}


@dataclass(frozen=True)
class LintIssue:
    code: str
    message: str
    path: Path
    severity: str = "error"  # "error" | "warning"


@dataclass
class LintResult:
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


class SchemaRegistry:
    """Loads all ``*.schema.json`` files from a directory and resolves the
    relative ``$ref`` values between them (e.g. ``okf.schema.json`` ->
    ``relations.schema.json``)."""

    def __init__(self, schema_dir: Path):
        self.schema_dir = Path(schema_dir)
        self._raw: dict[str, dict] = {}
        for schema_file in sorted(self.schema_dir.glob("*.schema.json")):
            self._raw[schema_file.name] = json.loads(schema_file.read_text(encoding="utf-8"))

        resources = []
        for name, schema in self._raw.items():
            resources.append((name, referencing.jsonschema.DRAFT7.create_resource(schema)))
            schema_id = schema.get("$id")
            if schema_id:
                resources.append((schema_id, referencing.jsonschema.DRAFT7.create_resource(schema)))
        self._registry = referencing.Registry().with_resources(resources)

    def validator_for_filename(self, filename: str) -> jsonschema.protocols.Validator:
        schema = self._raw[filename]
        return jsonschema.Draft7Validator(schema, registry=self._registry)

    def validator_for_type(self, okf_type: str) -> jsonschema.protocols.Validator:
        filename = _TYPE_SCHEMA_OVERRIDES.get(okf_type, "okf.schema.json")
        return self.validator_for_filename(filename)


def iter_okf_files(root: Path) -> Iterable[Path]:
    """Yield every Markdown file under ``root`` that is expected to carry OKF
    front matter (i.e. not a generated index or a plain README)."""
    for path in sorted(Path(root).rglob("*.md")):
        if path.name in _MARKDOWN_EXCLUDE_NAMES:
            continue
        yield path


def lint_document(document: OkfDocument, registry: SchemaRegistry) -> list[LintIssue]:
    issues: list[LintIssue] = []
    okf_type = document.front_matter.get("type")

    validator = registry.validator_for_type(okf_type) if okf_type else registry.validator_for_type("")
    for error in sorted(validator.iter_errors(document.front_matter), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in error.path) or "<root>"
        issues.append(
            LintIssue(
                code=SCHEMA_ERROR,
                message=f"{location}: {error.message}",
                path=document.path,
                severity="error",
            )
        )

    relations = document.front_matter.get("relations") or []
    relation_types = {r.get("type") for r in relations if isinstance(r, dict)}

    if okf_type == "user_story" and "tested_by" not in relation_types:
        issues.append(
            LintIssue(
                code=UNTESTED_USER_STORY,
                message="user_story has no 'tested_by' relation to a test_case (masterplan section 9.7)",
                path=document.path,
                severity="error",
            )
        )

    if okf_type == "spoc":
        for criterion in document.front_matter.get("output", {}).get("acceptance_criteria", []):
            if not criterion.get("test_case_refs"):
                issues.append(
                    LintIssue(
                        code=MISSING_TEST_CASE_REF,
                        message=(
                            f"acceptance criterion '{criterion.get('id')}' has no test_case_refs"
                        ),
                        path=document.path,
                        severity="warning",
                    )
                )

    return issues


def lint_directory(root: Path, registry: SchemaRegistry) -> LintResult:
    result = LintResult()
    seen_ids: dict[str, Path] = {}

    for path in iter_okf_files(root):
        try:
            document = load_okf_file(path)
        except Exception as exc:  # noqa: BLE001 - report as a lint issue, not a crash
            result.issues.append(
                LintIssue(code="OKF-PARSE-001", message=str(exc), path=path, severity="error")
            )
            continue

        result.issues.extend(lint_document(document, registry))

        doc_id = document.id
        if doc_id:
            if doc_id in seen_ids:
                result.issues.append(
                    LintIssue(
                        code=DUPLICATE_ID,
                        message=f"duplicate id '{doc_id}' also used by {seen_ids[doc_id]}",
                        path=path,
                        severity="error",
                    )
                )
            else:
                seen_ids[doc_id] = path

    return result
