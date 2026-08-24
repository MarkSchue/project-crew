"""Checksum manifests and provenance stamping (plan milestone M4.4).

- ``checksum_manifest``: writes ``artifacts/checksums/<run_id>.json``
  entries so every produced artifact is content-addressed.
- ``stamp_okf_provenance``: sets ``provenance.run_id`` in an OKF Markdown
  file's front matter without touching the body (masterplan section 9.1
  ``provenance`` block).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def checksum_entry(content: bytes) -> dict:
    return {
        "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def build_checksum_manifest(run_id: str, artifacts: dict[str, bytes]) -> dict:
    """``artifacts`` maps a repository-relative ref (e.g.
    ``public/deliverables/foo.md``) to its content bytes."""
    entries = {
        ref: checksum_entry(content) for ref, content in sorted(artifacts.items())
    }
    return {
        "schema_version": "checksum-manifest/1.0",
        "run_id": run_id,
        "artifacts": entries,
    }


def write_checksum_manifest(checksums_dir: Path, run_id: str, artifacts: dict[str, bytes]) -> Path:
    manifest = build_checksum_manifest(run_id, artifacts)
    output_dir = Path(checksums_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_id}.json"
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def stamp_okf_provenance(markdown_text: str, run_id: str) -> str:
    """Return `markdown_text` with ``provenance.run_id`` set to `run_id`,
    preserving the body and all other front-matter fields/formatting.

    - If a ``provenance:`` block exists, its ``run_id`` is set (or a new
      ``run_id`` line is inserted as the block's first key).
    - Otherwise a minimal ``provenance:`` block is appended to the front
      matter.
    """
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("not an OKF Markdown file: missing leading '---' front matter")

    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if closing is None:
        raise ValueError("not an OKF Markdown file: front matter not closed")

    front_matter = lines[1:closing]
    body = lines[closing + 1 :]

    prov_idx = next(
        (i for i, line in enumerate(front_matter) if line.strip() == "provenance:"), None
    )

    if prov_idx is None:
        front_matter = front_matter + ["provenance:", f"  run_id: {run_id}"]
    else:
        prov_indent = len(front_matter[prov_idx]) - len(front_matter[prov_idx].lstrip())
        # End of block: first subsequent non-empty line at indent <= prov_indent.
        block_end = len(front_matter)
        for j in range(prov_idx + 1, len(front_matter)):
            line = front_matter[j]
            stripped = line.strip()
            if stripped and (len(line) - len(line.lstrip())) <= prov_indent:
                block_end = j
                break

        block = front_matter[prov_idx:block_end]
        new_block: list[str] = []
        replaced = False
        for line in block:
            stripped = line.strip()
            if stripped.startswith("run_id:"):
                indent = len(line) - len(line.lstrip())
                new_block.append(" " * indent + f"run_id: {run_id}")
                replaced = True
            else:
                new_block.append(line)
        if not replaced:
            new_block.insert(1, " " * (prov_indent + 2) + f"run_id: {run_id}")
        front_matter = front_matter[:prov_idx] + new_block + front_matter[block_end:]

    return "\n".join(["---", *front_matter, "---", *body])


def stamp_okf_file(path: Path, run_id: str) -> None:
    text = Path(path).read_text(encoding="utf-8")
    Path(path).write_text(stamp_okf_provenance(text, run_id), encoding="utf-8")
