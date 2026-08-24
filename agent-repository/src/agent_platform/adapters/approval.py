"""In-memory ApprovalGateway adapter (plan M5.2 target port, used as a
Phase 3 test double per ADR-009).
"""

from __future__ import annotations

from agent_platform.domain.run import ApprovalRequest


class InMemoryApprovalGateway:
    def __init__(self, *, auto_approve: bool = False) -> None:
        self._auto_approve = auto_approve
        self._requests: dict[str, ApprovalRequest] = {}

    def request_approval(self, approval: ApprovalRequest) -> None:
        stored = approval.model_copy(deep=True)
        if self._auto_approve:
            stored.status = "approved"
        self._requests[approval.approval_id] = stored

    def get_status(self, approval_id: str) -> str:
        request = self._requests.get(approval_id)
        return request.status if request else "unknown"

    def resolve(self, approval_id: str, *, approved: bool, reason: str | None = None) -> None:
        request = self._requests.get(approval_id)
        if request is None:
            raise KeyError(f"unknown approval_id: {approval_id}")
        request.status = "approved" if approved else "rejected"
        request.reason = reason
