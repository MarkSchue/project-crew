"""Human approval service and states (masterplan section 15.7, plan
milestone M5.2, ADR-009).

Approval is a first-class, durable workflow state. This service owns:

- the mandatory-approval matrix (``approval_matrix.MANDATORY_APPROVAL_ACTIONS``);
- approval request lifecycle: pending -> approved | rejected | expired;
- expiry: an expired request blocks progress and cannot later be
  approved (it does not default to approved).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.control_plane.approval_matrix import MANDATORY_APPROVAL_ACTIONS
from agent_platform.domain.run import ApprovalRequest


def _parse_iso(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


class ApprovalService:
    def __init__(
        self,
        *,
        id_generator: IdGenerator,
        clock: Clock,
        approval_ttl_seconds: int | None = None,
    ) -> None:
        self.id_generator = id_generator
        self.clock = clock
        self.approval_ttl_seconds = approval_ttl_seconds
        self._requests: dict[str, ApprovalRequest] = {}

    # -- matrix ---------------------------------------------------------

    def requires_approval(self, action: str) -> bool:
        return action in MANDATORY_APPROVAL_ACTIONS

    # -- lifecycle --------------------------------------------------------

    def request(self, action: str, subject: str) -> ApprovalRequest:
        """Create a pending approval request for a mandatory-approval
        action. The approval id is derived from the action + subject so a
        duplicate request resolves to the same record."""
        approval_id = self.id_generator.new_id("approval")
        requested_at = self.clock.now_iso()
        expires_at = None
        if self.approval_ttl_seconds is not None:
            expires_at = _iso_after(requested_at, self.approval_ttl_seconds)

        request = ApprovalRequest(
            approval_id=approval_id,
            scope=action,
            subject=subject,
            status="pending",
            requested_at=requested_at,
            expires_at=expires_at,
        )
        self._requests[approval_id] = request
        return request

    def resolve(self, approval_id: str, *, approved: bool, reason: str | None = None) -> ApprovalRequest:
        request = self._requests.get(approval_id)
        if request is None:
            raise KeyError(f"unknown approval_id: {approval_id}")
        if self._is_expired(request):
            request.status = "expired"
            return request
        request.status = "approved" if approved else "rejected"
        request.reason = reason
        return request

    def get_status(self, approval_id: str) -> str:
        request = self._requests.get(approval_id)
        if request is None:
            return "unknown"
        if self._is_expired(request) and request.status == "pending":
            request.status = "expired"
        return request.status

    def is_approved(self, action: str, subject: str | None = None) -> bool:
        """True only if `action` does not require approval, or an explicit
        approved (non-expired) request exists for it. An expired request
        never counts as approved."""
        if action not in MANDATORY_APPROVAL_ACTIONS:
            return True
        for request in self._requests.values():
            if request.scope != action:
                continue
            if subject is not None and request.subject != subject:
                continue
            if self._is_expired(request):
                continue
            if request.status == "approved":
                return True
        return False

    def _is_expired(self, request: ApprovalRequest) -> bool:
        if request.expires_at is None:
            return False
        now = _parse_iso(self.clock.now_iso())
        return now > _parse_iso(request.expires_at)


def _iso_after(iso: str, seconds: int) -> str:
    dt = _parse_iso(iso)
    return (dt + timedelta(seconds=seconds)).isoformat()
