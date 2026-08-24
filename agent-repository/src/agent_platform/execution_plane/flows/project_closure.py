"""Project-closure flow (plan milestone M7.6, masterplan section 8.2 G5).

Blocks closure until unresolved risks and issues each have an owner, and
until every lesson proposed for promotion to global knowledge has an
explicit human approval record (``promote_private_knowledge``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_platform.control_plane.approval_service import ApprovalService
from agent_platform.execution_plane.flows.okf_render import okf_front_matter, render_okf


@dataclass(frozen=True)
class ClosureResult:
    complete: bool
    blockers: list[str] = field(default_factory=list)
    promoted_lessons: list[str] = field(default_factory=list)


def run_project_closure(
    *,
    unresolved_risks: list[dict],
    unresolved_issues: list[dict],
    lessons: list[dict],
    approval_service: ApprovalService,
) -> ClosureResult:
    blockers: list[str] = []
    for risk in unresolved_risks:
        if not (risk.get("owner") or "").strip():
            blockers.append(f"risk {risk.get('id', '?')} has no owner")
    for issue in unresolved_issues:
        if not (issue.get("owner") or "").strip():
            blockers.append(f"issue {issue.get('id', '?')} has no owner")

    promoted: list[str] = []
    for lesson in lessons:
        if lesson.get("promote_to_global"):
            lesson_id = lesson.get("id", "?")
            if approval_service.is_approved("promote_private_knowledge", lesson_id):
                promoted.append(lesson_id)
            else:
                blockers.append(f"lesson {lesson_id} lacks promotion approval")

    return ClosureResult(complete=not blockers, blockers=blockers, promoted_lessons=promoted)


def render_closure_artifact(
    *,
    project_id: str,
    result: ClosureResult,
    owner: str = "project_manager",
    classification: str = "internal",
    timestamp: str | None = None,
) -> str:
    state = "closure approved" if result.complete else "closure blocked"
    promoted_lines = [f"- {lesson_id}" for lesson_id in result.promoted_lessons] or ["- (none)"]
    blocker_lines = [f"- {blocker}" for blocker in result.blockers] or ["- (none)"]
    body_lines = [
        "# Project closure",
        "",
        f"State: {state}.",
        "",
        "## Promoted lessons",
        *promoted_lines,
        "",
        "## Remaining blockers",
        *blocker_lines,
        "",
    ]
    return render_okf(
        okf_front_matter(
            okf_id=f"CLOSURE-{project_id}",
            okf_type="concept",
            title="Project closure",
            status="approved" if result.complete else "draft",
            owner=owner,
            classification=classification,
            timestamp=timestamp,
        ),
        "\n".join(body_lines),
    )
