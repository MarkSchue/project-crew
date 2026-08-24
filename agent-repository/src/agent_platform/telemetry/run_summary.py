"""Run summary generator (masterplan section 16.3, plan milestone M3.9).

Generates the OKF `summary.md` content for a completed run attempt, with
`generated_by` back to the SPOC and `evidenced_by` forward to the run's
`events.jsonl`, including every test result produced during the run
(masterplan section 9.5).
"""

from __future__ import annotations

from agent_platform.domain.events import RunEvent
from agent_platform.domain.run import ProjectRunState


def _test_case_events(events: list[RunEvent]) -> list[RunEvent]:
    return [e for e in events if e.event_type == "test_case_executed"]


def generate_run_summary_markdown(state: ProjectRunState, events: list[RunEvent]) -> str:
    manifest = state.manifest
    test_case_events = _test_case_events(events)

    lines = [
        "---",
        'schema_version: "okf/1.1"',
        f'id: "RUN-SUMMARY-{manifest.run_id}"',
        'type: "run_summary"',
        f'title: "Run summary for {manifest.spoc_id}"',
        f'status: "{state.status.value}"',
        'classification: "internal"',
        'owner: "platform"',
        "relations:",
        f'  - type: "generated_by"',
        f'    target: "{manifest.spoc_id}"',
        f'  - type: "evidenced_by"',
        f'    target: "events.jsonl"',
        "---",
        "",
        f"# Run summary: {manifest.run_id} / attempt {manifest.attempt_id}",
        "",
        f"- SPOC: `{manifest.spoc_id}` (version `{manifest.spoc_version}`)",
        f"- Execution key: `{manifest.execution_key}`",
        f"- Workflow: `{manifest.workflow_id}@{manifest.workflow_version}`",
        f"- Final status: `{state.status.value}`",
        f"- QA rework attempts: {state.qa_rework_count}",
        "",
        "## Resolved agents",
        "",
    ]
    for agent in state.resolved_agents:
        lines.append(f"- `{agent.agent_id}` ({agent.role}, score {agent.score})")

    lines += ["", "## Test results", ""]
    if test_case_events:
        for event in test_case_events:
            passed = event.payload.get("passed")
            outcome = "PASS" if passed else "FAIL"
            lines.append(f"- `{event.payload.get('test_case_id')}`: {outcome}")
    else:
        lines.append("(no test cases executed)")

    lines += ["", "## Validation results", ""]
    for validation in state.validation_results:
        lines.append(f"- `{validation.validator}`: {'PASS' if validation.passed else 'FAIL'}")

    lines += ["", "## Errors", ""]
    if state.errors:
        for error in state.errors:
            lines.append(f"- `{error.error_code}`: {error.message}")
    else:
        lines.append("(none)")

    lines.append("")
    return "\n".join(lines)
