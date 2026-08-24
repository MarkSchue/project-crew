"""Pull-request body generation (masterplan section 14.5, plan milestone
M4.3).

A generated PR body must include links to the run summary, test results,
and the human approval record (if any) so a reviewer can navigate from
the PR to the evidence that produced it.
"""

from __future__ import annotations


def build_pull_request_body(
    *,
    title: str,
    spoc_id: str,
    run_id: str,
    run_summary_ref: str,
    test_result_refs: list[str],
    approval_ref: str | None = None,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- **SPOC:** `{spoc_id}`",
        f"- **Run:** `{run_id}`",
        "",
        "## Validation evidence",
        "",
        f"- Run summary: [{run_summary_ref}]({run_summary_ref})",
    ]
    if test_result_refs:
        lines.append("- Test results:")
        for ref in test_result_refs:
            lines.append(f"  - [{ref}]({ref})")
    if approval_ref:
        lines.append(f"- Human approval: [{approval_ref}]({approval_ref})")
    lines += [
        "",
        "## Review checklist",
        "",
        "- [ ] Run summary reviewed",
        "- [ ] All linked test results passing",
        "- [ ] Human approval present (if required by the SPOC approval policy)",
    ]
    return "\n".join(lines) + "\n"
