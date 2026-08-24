"""RunStateStore port (plan section 19.5, ADR-012).

The single authoritative checkpoint for a run's ``ProjectRunState``. If
CrewAI Flow persistence is ever used, it must be implemented as an
adapter behind this port, never as an independent second store
(ADR-012).
"""

from __future__ import annotations

from typing import Protocol

from agent_platform.domain.run import ProjectRunState


class RunStateStore(Protocol):
    def save(self, run_id: str, attempt_id: str, state: ProjectRunState) -> None: ...

    def load(self, run_id: str, attempt_id: str) -> ProjectRunState | None: ...

    def latest_attempt_id(self, run_id: str) -> str | None: ...

    def delete(self, run_id: str, attempt_id: str) -> None: ...

    def list_run_ids(self) -> list[str]: ...
