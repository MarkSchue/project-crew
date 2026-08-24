"""Match explanation report (masterplan section 12.2; plan milestone M2.4).

Renders a machine-readable (dict, JSON-serializable) and human-readable
(Markdown) explanation of why an agent was selected or rejected, with the
score breakdown accounting for 100% of the configured (non-zero) score
weight.
"""

from __future__ import annotations

from agent_platform.control_plane.capability_matcher import MatchResult


def explain_match_json(result: MatchResult) -> dict:
    return {
        "required_capabilities": sorted(result.required_capabilities),
        "primary": (
            {
                "agent_id": result.primary.agent_id,
                "score": result.primary.score,
                "score_breakdown": result.primary.score_breakdown,
                "covered_capabilities": sorted(result.primary.covered_capabilities),
            }
            if result.primary
            else None
        ),
        "delegate_candidates": [
            {
                "agent_id": c.agent_id,
                "score": c.score,
                "score_breakdown": c.score_breakdown,
                "covered_capabilities": sorted(c.covered_capabilities),
            }
            for c in result.delegate_candidates
        ],
        "unresolved_capabilities": sorted(result.unresolved_capabilities),
        "ranked": [
            {
                "agent_id": c.agent_id,
                "score": c.score,
                "score_breakdown": c.score_breakdown,
                "covered_capabilities": sorted(c.covered_capabilities),
            }
            for c in result.ranked
        ],
        "rejected": [{"agent_id": r.agent_id, "reason": r.reason} for r in result.rejected],
    }


def explain_match_markdown(result: MatchResult) -> str:
    lines = ["# Capability match explanation", ""]
    lines.append(f"Required capabilities: {', '.join(sorted(result.required_capabilities)) or '(none)'}")
    lines.append("")

    if result.primary:
        lines.append(f"## Primary agent: `{result.primary.agent_id}` (score {result.primary.score:.4f})")
        lines.append("")
        lines.append("| factor | weighted contribution |")
        lines.append("|---|---|")
        total = 0.0
        for factor, contribution in result.primary.score_breakdown.items():
            lines.append(f"| {factor} | {contribution:.4f} |")
            total += contribution
        lines.append(f"| **total** | **{total:.4f}** |")
        lines.append("")
    else:
        lines.append("## No agent selected")
        lines.append("")

    if result.delegate_candidates:
        lines.append("## Delegate candidates")
        for candidate in result.delegate_candidates:
            covered = ", ".join(sorted(candidate.covered_capabilities))
            lines.append(f"- `{candidate.agent_id}` (score {candidate.score:.4f}) covers: {covered}")
        lines.append("")

    if result.unresolved_capabilities:
        lines.append("## Unresolved capabilities")
        for cid in sorted(result.unresolved_capabilities):
            lines.append(f"- {cid}")
        lines.append("")

    if result.rejected:
        lines.append("## Rejected candidates")
        lines.append("")
        lines.append("| agent | failing hard filter |")
        lines.append("|---|---|")
        for rejection in result.rejected:
            lines.append(f"| {rejection.agent_id} | {rejection.reason} |")
        lines.append("")

    return "\n".join(lines)
