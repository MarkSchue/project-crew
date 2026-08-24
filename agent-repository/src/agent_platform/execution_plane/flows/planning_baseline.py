"""Planning/baseline flow (masterplan section 8.2 G2, plan milestone
M7.1).

Produces the G2 artifacts as OKF Markdown: work breakdown structure,
milestone deliverable, acceptance strategy, an initial risk and
dependency, and — crucially — one epic with a linked, test-covered user
story (masterplan section 8.3 work hierarchy, 9.7 traceability):

- ``EPIC-001`` (epic)
- ``US-001`` (user_story, ``part_of`` EPIC-001, ``tested_by`` TC-001)
- ``TC-001`` (test_case, ``validates`` US-001)

All outputs pass the Phase 1 validators (lint + cross-reference).
"""

from __future__ import annotations

from agent_platform.execution_plane.flows.okf_render import okf_front_matter, relation, render_okf


def run_planning_baseline(project: dict, *, timestamp: str | None = None) -> dict[str, str]:
    project_id = project["project_id"]
    name = project.get("name", project_id)
    owner = project.get("owner", "project_manager")
    classification = project.get("classification", "internal")
    goal = project.get("goal", {})
    outcomes = project.get("outcomes", []) or []

    def doc(okf_id: str, okf_type: str, title: str, body: str, *, status: str = "approved", relations=None):
        return render_okf(
            okf_front_matter(
                okf_id=okf_id,
                okf_type=okf_type,
                title=title,
                status=status,
                owner=owner,
                classification=classification,
                relations=relations,
                timestamp=timestamp,
            ),
            body,
        )

    outcome_lines = "\n".join(f"- {o.get('id', '?')}: {o.get('statement', '')}" for o in outcomes) or "- (none)"

    artifacts = {
        "public/plans/wbs.md": doc(
            f"WBS-{project_id}",
            "concept",
            "Work breakdown structure",
            f"# Work breakdown structure\n\n- Milestone MS-001: {goal.get('target_state', name)}\n- Epic EPIC-001: initial deliverable scope\n\nOutcomes:\n{outcome_lines}\n",
        ),
        "public/deliverables/DEL-001.md": doc(
            "DEL-001",
            "deliverable",
            "Milestone MS-001 deliverable",
            "# Milestone MS-001 deliverable\n\nInitial planning baseline deliverable.\n",
        ),
        "public/acceptance/acceptance_strategy.md": doc(
            f"ACCEPT-{project_id}",
            "acceptance",
            "Acceptance strategy",
            "# Acceptance strategy\n\nEvery acceptance criterion is validated by a linked test case executed by the QA agent (masterplan section 13.5).\n",
        ),
        "public/architecture/constraints.md": doc(
            f"ARCHCONST-{project_id}",
            "concept",
            "Architecture constraints",
            "# Architecture constraints\n\n- Deterministic matching and policy gates are mandatory.\n- Project artifacts remain usable without CrewAI (masterplan principle 13).\n",
        ),
        "public/risks/RISK-001.md": doc(
            "RISK-001",
            "risk",
            "Initial delivery risk",
            "# RISK-001\n\nInitial delivery risk recorded during planning baseline.\n",
            status="open",
        ),
        "public/dependencies/DEP-001.md": doc(
            "DEP-001",
            "dependency",
            "Initial external dependency",
            "# DEP-001\n\nInitial external dependency recorded during planning baseline.\n",
            status="open",
        ),
        "public/epics/EPIC-001.md": doc(
            "EPIC-001",
            "epic",
            "Initial delivery epic",
            "# EPIC-001\n\nInitial deliverable scope for the planning baseline.\n",
        ),
        "public/user_stories/US-001.md": doc(
            "US-001",
            "user_story",
            "First user story",
            "# US-001\n\nAs a stakeholder, I want the first deliverable so that the project goal is advanced.\n",
            status="ready",
            relations=[relation("part_of", "EPIC-001"), relation("tested_by", "TC-001")],
        ),
        "public/test_cases/TC-001.md": doc(
            "TC-001",
            "test_case",
            "Acceptance test for US-001",
            "# TC-001\n\nVerifies US-001 against its acceptance criteria.\n",
            status="active",
            relations=[relation("validates", "US-001")],
        ),
    }

    return artifacts
