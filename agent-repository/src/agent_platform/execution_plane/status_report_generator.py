"""Status-report generator (plan milestone M7.5, masterplan section 8.5).

Produces an OKF ``status_report`` whose every claim is traced via a
``reports_on`` relation (and rendered ``[ref: ...]`` anchor) so that zero
unsourced claims are enforced by an automated check.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.execution_plane.flows.okf_render import okf_front_matter, relation, render_okf


@dataclass(frozen=True)
class StatusClaim:
    statement: str
    source_ref: str  # artifact id the claim reports on


def generate_status_report(
    *,
    project_id: str,
    report_id: str,
    claims: list[StatusClaim],
    owner: str = "project_manager",
    classification: str = "internal",
    timestamp: str | None = None,
) -> str:
    relations = [relation("reports_on", c.source_ref) for c in claims]
    body_lines = ["# Status report", "", "## Claims", ""]
    for claim in claims:
        body_lines.append(f"- {claim.statement} [ref: {claim.source_ref}]")
    body_lines.append("")
    body = "\n".join(body_lines)

    return render_okf(
        okf_front_matter(
            okf_id=report_id,
            okf_type="status_report",
            title=f"Status report {report_id}",
            status="active",
            owner=owner,
            classification=classification,
            relations=relations,
            timestamp=timestamp,
        ),
        body,
    )


def find_unsourced_claims(markdown: str) -> list[str]:
    """Return claim bullets in the ``## Claims`` section that lack a
    ``[ref: ...]`` anchor. An empty list means the report is fully
    sourced."""
    unsourced: list[str] = []
    in_claims = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped == "## Claims":
            in_claims = True
            continue
        if in_claims and stripped.startswith("## "):
            in_claims = False
            continue
        if in_claims and stripped.startswith("- "):
            if "[ref:" not in stripped:
                unsourced.append(stripped)
    return unsourced
