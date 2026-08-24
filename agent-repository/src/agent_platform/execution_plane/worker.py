"""Queue-backed worker with lease recovery (masterplan section 18.3, plan
milestone M6.3, ADR-017).

The worker pulls a compiled manifest, acquires a time-limited lease with
heartbeat renewal, executes the canonical Flow, and releases the lease.
If a previous worker crashed, the lease is expired and this worker takes
it over after reconciling: it reads the persisted ``RunStateStore`` state
and resumes from the last completed step instead of re-executing prior
side effects.

The queue itself is abstracted: this worker exposes ``run_once`` against
a manifest it is handed (the queue/lease table from ADR-017 is the
dispatcher's concern); the lease store here is the lease-management half.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from agent_platform.application.ports.clock_and_ids import Clock
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import RunManifest
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _iso_after(iso: str, seconds: int) -> str:
    return (_parse_iso(iso) + timedelta(seconds=seconds)).isoformat()


@dataclass(frozen=True)
class Lease:
    run_id: str
    owner: str
    expires_at: str


class LeaseUnavailableError(Exception):
    code = "LEASE_UNAVAILABLE"


class InMemoryLeaseStore:
    def __init__(self) -> None:
        self._leases: dict[str, Lease] = {}

    def acquire(self, run_id: str, owner: str, ttl_seconds: int, now_iso: str, *, force: bool = False) -> bool:
        existing = self._leases.get(run_id)
        if existing is not None and not force:
            if _parse_iso(now_iso) <= _parse_iso(existing.expires_at):
                return False  # still held by another owner
            # else: expired -> takeover is allowed below
        self._leases[run_id] = Lease(run_id=run_id, owner=owner, expires_at=_iso_after(now_iso, ttl_seconds))
        return True

    def renew(self, run_id: str, owner: str, ttl_seconds: int, now_iso: str) -> bool:
        existing = self._leases.get(run_id)
        if existing is None or existing.owner != owner:
            return False
        self._leases[run_id] = Lease(run_id=run_id, owner=owner, expires_at=_iso_after(now_iso, ttl_seconds))
        return True

    def release(self, run_id: str, owner: str) -> None:
        existing = self._leases.get(run_id)
        if existing is not None and existing.owner == owner:
            del self._leases[run_id]

    def get(self, run_id: str) -> Lease | None:
        return self._leases.get(run_id)

    def is_expired(self, lease: Lease, now_iso: str) -> bool:
        return _parse_iso(now_iso) > _parse_iso(lease.expires_at)


@dataclass
class Worker:
    flow: ProjectExecutionFlow
    lease_store: InMemoryLeaseStore
    clock: Clock
    owner: str = "worker-1"

    def run_once(
        self,
        manifest: RunManifest,
        options: FlowRunOptions,
        *,
        ttl_seconds: int = 30,
    ) -> object:
        """Acquire (or recover) the lease for `manifest.run_id`, execute
        the flow, and release the lease. Returns the final
        ``ProjectRunState``."""
        run_id = manifest.run_id

        prior = self.lease_store.get(run_id)
        took_over_expired = prior is not None and self.lease_store.is_expired(prior, self.clock.now_iso())

        acquired = self.lease_store.acquire(run_id, self.owner, ttl_seconds, self.clock.now_iso())
        if not acquired:
            existing = self.lease_store.get(run_id)
            raise LeaseUnavailableError(
                f"lease for '{run_id}' is held by {existing.owner if existing else '?'}"
            )

        if took_over_expired:
            # Recover a lease left behind by a crashed worker: reconcile
            # prior side effects from the persisted state before resuming.
            self._reconcile(manifest)

        try:
            return self.flow.start(manifest, options)
        finally:
            self.lease_store.release(run_id, self.owner)

    def _reconcile(self, manifest: RunManifest) -> None:
        """Before resuming a recovered lease, detect prior side effects
        from the persisted state and record a reconciliation event so the
        takeover is auditable."""
        prior = self.flow.run_state_store.load(manifest.run_id, manifest.attempt_id)
        prior_steps = prior.completed_steps if prior else []
        if prior_steps:
            self.flow.event_ledger.append(
                RunEvent(
                    event_id=self.flow.id_generator.new_id("evt"),
                    run_id=manifest.run_id,
                    attempt_id=manifest.attempt_id,
                    step_id="lease_reconciliation",
                    aggregate_id=manifest.run_id,
                    event_type="lease_reconciliation",
                    timestamp=self.flow.clock.now_iso(),
                    actor=Actor(type="system", id=self.owner),
                    payload={"prior_completed_steps": prior_steps},
                )
            )
