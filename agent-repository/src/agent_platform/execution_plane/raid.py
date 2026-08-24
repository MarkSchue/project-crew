"""RAID and decision-log tooling (plan milestone M7.4, masterplan section
8.4).

Creates ``public/risks``, ``public/issues``, ``public/dependencies`` and
``public/decisions`` OKF files and — critically — enforces the ``blocks``
dependency gate: a SPOC whose id is ``blocks``-targeted by an unresolved
dependency cannot be matched or executed (masterplan section 8.4).
"""

from __future__ import annotations

from agent_platform.execution_plane.flows.okf_render import okf_front_matter, relation, render_okf

_UNRESOLVED = ("open", "in_progress", "identified")


def raid_document(
    *,
    doc_id: str,
    doc_type: str,
    title: str,
    status: str,
    owner: str,
    classification: str,
    body: str,
    relations: list[dict] | None = None,
    timestamp: str | None = None,
) -> str:
    """Render a single RAID/decision OKF Markdown document."""
    return render_okf(
        okf_front_matter(
            okf_id=doc_id,
            okf_type=doc_type,
            title=title,
            status=status,
            owner=owner,
            classification=classification,
            relations=relations,
            timestamp=timestamp,
        ),
        body,
    )


def dependency_document(
    *,
    dep_id: str,
    title: str,
    status: str,
    owner: str,
    blocks: list[str],
    classification: str = "internal",
    timestamp: str | None = None,
) -> str:
    """Render a dependency that ``blocks`` one or more SPOC ids."""
    relations = [relation("blocks", spoc_id) for spoc_id in blocks]
    body = f"# {dep_id}\n\nDependency blocking: {', '.join(blocks) or '(none)'}.\n"
    return raid_document(
        doc_id=dep_id,
        doc_type="dependency",
        title=title,
        status=status,
        owner=owner,
        classification=classification,
        body=body,
        relations=relations,
        timestamp=timestamp,
    )


def check_blocked(spoc_id: str, dependencies: dict[str, dict]) -> list[str]:
    """Return the ids of dependencies that block `spoc_id` and are not yet
    resolved."""
    blockers: list[str] = []
    for dep_id, dep in dependencies.items():
        status = (dep.get("status") or "open").lower()
        blocks = dep.get("blocks") or []
        if spoc_id in blocks and status in _UNRESOLVED:
            blockers.append(dep_id)
    return sorted(blockers)
