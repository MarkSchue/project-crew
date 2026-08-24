"""Append-only JSONL event projector (masterplan section 16, plan section
22.1 step 3, ADR-013).

The database/`EventLedger` is authoritative; this module projects its
events into the portable, human/agent-readable `events.jsonl` evidence
file. It never rewrites a line already written (write-once, verified by
test): re-running the projector only appends events whose `event_id` is
not already present in the target file.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_platform.domain.events import RunEvent


def _existing_event_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            ids.add(record["event_id"])
    return ids


def project_events_to_jsonl(events: list[RunEvent], output_path: Path) -> int:
    """Append every event in `events` whose `event_id` is not already
    present in `output_path`. Returns the number of newly written lines.
    Never opens the file in a mode that could truncate or rewrite an
    existing line."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    already_written = _existing_event_ids(output_path)

    new_events = [e for e in events if e.event_id not in already_written]
    if not new_events:
        return 0

    with output_path.open("a", encoding="utf-8") as fh:
        for event in new_events:
            fh.write(json.dumps(event.model_dump(), sort_keys=True) + "\n")

    return len(new_events)
