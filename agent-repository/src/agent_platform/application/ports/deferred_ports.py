"""Remaining Phase 4+ application ports (plan section 20.1), defined now as
thin Protocols so execution-plane code can depend on the full port set
from day one, per plan section 20.2. Concrete adapters for these ports are
out of scope for Phase 3 and are implemented in later phases:

- ``ArtifactRepository`` / ``ObjectStore``: Phase 4 (ADR-018).
- ``GitWorkspace``: Phase 4 (branch-per-run, ADR-006).
- ``ModelGateway``: Phase 5 (model routing).
- ``AgentRuntime``: Phase 3 continuation / Phase 5 (real CrewAI-backed
  execution; Phase 3 here uses a minimal in-process stand-in, see
  ``agent_platform.adapters.agent_runtime``).
- ``IdentityContext`` / ``SecretsProvider``: Phase 5/6.
- ``BudgetMeter``: Phase 5 (cost/token ceilings).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ArtifactRepository(Protocol):
    def read(self, ref: str) -> bytes: ...

    def write(self, ref: str, content: bytes) -> str: ...  # returns content hash


class ObjectStore(Protocol):
    def put(self, key: str, content: bytes) -> str: ...  # returns content hash

    def get(self, key: str) -> bytes: ...


class GitWorkspace(Protocol):
    def create_run_branch(self, run_id: str) -> str: ...

    def commit(self, branch: str, message: str) -> str: ...  # returns commit hash

    def open_pull_request(self, branch: str, title: str, body: str) -> str: ...  # returns PR url/id


class ModelGateway(Protocol):
    def complete(self, *, profile_id: str, prompt: str) -> str: ...


class AgentRuntime(Protocol):
    def run_agent(self, *, agent_id: str, task_input: dict) -> dict: ...


class IdentityContext(Protocol):
    def current_actor(self) -> tuple[str, str]: ...  # (actor_type, actor_id)


@dataclass(frozen=True)
class BudgetCheckResult:
    allowed: bool
    reason: str


class BudgetMeter(Protocol):
    def check(self, *, estimated_cost_usd: float, cost_state: dict) -> BudgetCheckResult: ...


class SecretsProvider(Protocol):
    def get_secret(self, name: str) -> str: ...
