"""Deterministic canonicalization and content hashing for OKF/SPOC front matter.

Implements masterplan section 9.2: "Hashes are calculated after
canonicalization and excluded from the hash input itself."
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FRONT_MATTER_DELIMITER = "---"
HASH_EXCLUDED_FIELDS = {"content_hash"}


class FrontMatterError(ValueError):
    """Raised when a Markdown file does not contain valid OKF front matter."""


@dataclass(frozen=True)
class OkfDocument:
    """A parsed OKF Markdown file: YAML front matter plus Markdown body."""

    path: Path
    front_matter: dict[str, Any]
    body: str

    @property
    def id(self) -> str | None:
        return self.front_matter.get("id")

    @property
    def type(self) -> str | None:
        return self.front_matter.get("type")


def split_front_matter(text: str) -> tuple[str, str]:
    """Split raw Markdown text into (front_matter_yaml, body).

    The file must start with a line containing only ``---``, followed by
    YAML, a closing ``---`` line, and then the Markdown body.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_DELIMITER:
        raise FrontMatterError("File does not start with a '---' front matter delimiter")
    try:
        closing_index = next(
            i for i in range(1, len(lines)) if lines[i].strip() == FRONT_MATTER_DELIMITER
        )
    except StopIteration as exc:
        raise FrontMatterError("Front matter is not closed with a '---' delimiter") from exc

    front_matter_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])
    return front_matter_text, body


def parse_okf_text(text: str, path: Path | None = None) -> OkfDocument:
    """Parse raw Markdown text into an :class:`OkfDocument`."""
    front_matter_text, body = split_front_matter(text)
    try:
        front_matter = yaml.safe_load(front_matter_text) or {}
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"Invalid YAML front matter: {exc}") from exc
    if not isinstance(front_matter, dict):
        raise FrontMatterError("Front matter must be a YAML mapping")
    return OkfDocument(path=path or Path("<memory>"), front_matter=front_matter, body=body)


def load_okf_file(path: Path) -> OkfDocument:
    """Read and parse an OKF Markdown file from disk."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_okf_text(text, path=Path(path))


def _canonical_json(value: Any) -> str:
    """Render a JSON-compatible value deterministically: sorted keys, no
    insignificant whitespace, stable separators."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonicalize_front_matter(front_matter: dict[str, Any]) -> str:
    """Canonicalize front matter for hashing, excluding hash-carrying fields."""
    filtered = {k: v for k, v in front_matter.items() if k not in HASH_EXCLUDED_FIELDS}
    return _canonical_json(filtered)


def compute_content_hash(front_matter: dict[str, Any], body: str) -> str:
    """Compute the deterministic ``sha256:<hex>`` content hash for a document."""
    canonical = canonicalize_front_matter(front_matter) + "\n" + body.strip() + "\n"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_content_hash(document: OkfDocument) -> bool:
    """Return True if the document's recorded ``content_hash`` matches its
    recomputed hash, or if it does not declare one at all."""
    declared = document.front_matter.get("content_hash")
    if declared is None:
        return True
    return declared == compute_content_hash(document.front_matter, document.body)
