"""Project intake flow (masterplan section 8.2 G0/G1, plan milestone
M7.1).

Produces the G0/G1 stage-gate artifacts as OKF Markdown: the project
charter (objective, target state, business value), initial constraints,
and decision rights. The artifacts are plain OKF files that pass the
Phase 1 validators; the G0/G1 *approval events* are recorded through the
ApprovalService (M5.2), not impersonated here (masterplan section 8.2:
"agents may prepare evidence but may not impersonate human approvers").
"""

from __future__ import annotations

from agent_platform.execution_plane.flows.okf_render import okf_front_matter, render_okf


def run_project_intake(project: dict, *, timestamp: str | None = None) -> dict[str, str]:
    """Return a mapping of repository-relative path -> OKF Markdown text
    for the intake artifacts."""
    project_id = project["project_id"]
    name = project.get("name", project_id)
    owner = project.get("owner", "project_sponsor")
    classification = project.get("classification", "internal")
    goal = project.get("goal", {})
    constraints = project.get("constraints", []) or []

    charter_body = (
        f"# Project charter: {name}\n\n"
        f"- Objective: {goal.get('statement', '(not stated)')}\n"
        f"- Target state: {goal.get('target_state', '(not stated)')}\n"
        f"- Business value: {goal.get('business_value', '(not stated)')}\n"
    )
    charter = render_okf(
        okf_front_matter(
            okf_id=f"CHARTER-{project_id}",
            okf_type="concept",
            title=f"Project charter: {name}",
            status="approved",
            owner=owner,
            classification=classification,
            timestamp=timestamp,
        ),
        charter_body,
    )

    constraints_lines = "\n".join(f"- {c}" for c in constraints) or "- (none)"
    constraints_doc = render_okf(
        okf_front_matter(
            okf_id=f"CONSTRAINTS-{project_id}",
            okf_type="concept",
            title="Initial constraints",
            status="approved",
            owner=owner,
            classification=classification,
            timestamp=timestamp,
        ),
        f"# Initial constraints\n\n{constraints_lines}\n",
    )

    decision_rights = render_okf(
        okf_front_matter(
            okf_id=f"DECRIGHTS-{project_id}",
            okf_type="decision",
            title="Decision rights",
            status="approved",
            owner=owner,
            classification=classification,
            timestamp=timestamp,
        ),
        (
            f"# Decision rights\n\nOwner of record: {owner}.\n\n"
            "Human approval is mandatory for the actions in masterplan "
            "section 15.7 (scope/budget/baseline change, access expansion, "
            "policy exception, high-risk inferred capability, external "
            "communication, production change, legal/regulatory conclusions, "
            "knowledge promotion, agent/tool activation).\n"
        ),
    )

    return {
        "public/charter/project_charter.md": charter,
        "public/charter/initial_constraints.md": constraints_doc,
        "public/decisions/decision_rights.md": decision_rights,
    }
