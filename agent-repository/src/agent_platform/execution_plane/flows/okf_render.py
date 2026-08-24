"""OKF rendering helpers for project-management workflows.

Builds valid ``okf/1.1`` Markdown (front matter + body) for the G0-G5
stage-gate artifacts. All outputs must pass ``mas project validate``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import yaml


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def okf_front_matter(
    *,
    okf_id: str,
    okf_type: str,
    title: str,
    status: str,
    owner: str,
    classification: str = "internal",
    tags: list[str] | None = None,
    relations: list[dict] | None = None,
    created_by_id: str = "project_workflows",
    timestamp: str | None = None,
) -> dict:
    ts = timestamp or now_iso()
    return {
        "schema_version": "okf/1.1",
        "id": okf_id,
        "type": okf_type,
        "title": title,
        "status": status,
        "classification": classification,
        "owner": owner,
        "created_at": ts,
        "updated_at": ts,
        "tags": tags or [],
        "source_refs": [],
        "relations": relations or [],
        "provenance": {"created_by_type": "system", "created_by_id": created_by_id, "run_id": None},
    }


def render_okf(front_matter: dict, body: str) -> str:
    """Render an OKF Markdown document from a front-matter mapping and a
    body. Front matter is emitted as YAML (sorted keys off, preserving the
    caller's order)."""
    yaml_block = yaml.safe_dump(front_matter, sort_keys=False, default_flow_style=False, allow_unicode=True).rstrip("\n")
    return f"---\n{yaml_block}\n---\n{body}\n"


def relation(rel_type: str, target: str) -> dict:
    return {"type": rel_type, "target": target}
