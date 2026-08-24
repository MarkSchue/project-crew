from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import ProjectRunState, RunManifest, RunStatus, ValidationResult
from agent_platform.telemetry.run_summary import generate_run_summary_markdown


def _manifest() -> RunManifest:
    return RunManifest(
        project_id="PRJ-001",
        spoc_id="SPOC-2026-0042",
        spoc_version="sha256:abc",
        execution_key="execkey_abc",
        run_id="run_1",
        attempt_id="attempt_1",
        correlation_id="corr_1",
        workflow_id="requirement_to_delivery",
        workflow_version="1.2.0",
    )


def test_run_summary_links_back_to_spoc_and_forward_to_events():
    state = ProjectRunState(manifest=_manifest(), status=RunStatus.CLOSED)
    state.validation_results.append(ValidationResult(validator="output_artifact_presence", passed=True))

    events = [
        RunEvent(
            event_id="evt_1",
            run_id="run_1",
            attempt_id="attempt_1",
            aggregate_id="run_1",
            event_type="test_case_executed",
            timestamp="2026-08-24T09:00:00Z",
            actor=Actor(type="agent", id="qa_evaluator"),
            payload={"test_case_id": "AC-1", "passed": True},
        )
    ]

    markdown = generate_run_summary_markdown(state, events)

    assert 'target: "SPOC-2026-0042"' in markdown
    assert 'type: "generated_by"' in markdown
    assert 'type: "evidenced_by"' in markdown
    assert "AC-1" in markdown
    assert "PASS" in markdown


def test_run_summary_reports_failing_test_cases_and_errors():
    state = ProjectRunState(manifest=_manifest(), status=RunStatus.DEAD_LETTER)
    from agent_platform.domain.run import RunError

    state.errors.append(RunError(error_code="qa_exhausted_retries", message="max attempts reached"))

    events = [
        RunEvent(
            event_id="evt_1",
            run_id="run_1",
            attempt_id="attempt_1",
            aggregate_id="run_1",
            event_type="test_case_executed",
            timestamp="2026-08-24T09:00:00Z",
            actor=Actor(type="agent", id="qa_evaluator"),
            payload={"test_case_id": "AC-2", "passed": False},
        )
    ]

    markdown = generate_run_summary_markdown(state, events)

    assert "FAIL" in markdown
    assert "qa_exhausted_retries" in markdown
