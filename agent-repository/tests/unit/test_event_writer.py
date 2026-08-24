import json

from agent_platform.domain.events import Actor, RunEvent
from agent_platform.telemetry.event_writer import project_events_to_jsonl


def _make_event(event_id: str) -> RunEvent:
    return RunEvent(
        event_id=event_id,
        run_id="run_1",
        attempt_id="attempt_1",
        aggregate_id="run_1",
        event_type="test_event",
        timestamp="2026-08-24T09:00:00Z",
        actor=Actor(type="system", id="test"),
    )


def test_project_events_writes_all_new_events(tmp_path):
    output_path = tmp_path / "events.jsonl"
    events = [_make_event("evt_1"), _make_event("evt_2")]

    written = project_events_to_jsonl(events, output_path)

    assert written == 2
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event_id"] == "evt_1"


def test_project_events_is_append_only_and_does_not_duplicate(tmp_path):
    output_path = tmp_path / "events.jsonl"
    project_events_to_jsonl([_make_event("evt_1")], output_path)
    original_content = output_path.read_text(encoding="utf-8")

    # Re-running with the same event plus one new one only appends the new one.
    written = project_events_to_jsonl([_make_event("evt_1"), _make_event("evt_2")], output_path)

    assert written == 1
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith(original_content)  # existing line untouched
    lines = content.strip().splitlines()
    assert len(lines) == 2


def test_project_events_with_no_new_events_returns_zero(tmp_path):
    output_path = tmp_path / "events.jsonl"
    project_events_to_jsonl([_make_event("evt_1")], output_path)
    written = project_events_to_jsonl([_make_event("evt_1")], output_path)
    assert written == 0
