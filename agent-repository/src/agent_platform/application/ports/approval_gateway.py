"""ApprovalGateway port (masterplan section 10.3, plan section, ADR-009).

Approval is a first-class, durable Flow state, not a chat convention
(ADR-009). This port persists approval requests and their resolution.
"""

from __future__ import annotations

from typing import Protocol

from agent_platform.domain.run import ApprovalRequest


class ApprovalGateway(Protocol):
    def request_approval(self, approval: ApprovalRequest) -> None: ...

    def get_status(self, approval_id: str) -> str: ...

    def resolve(self, approval_id: str, *, approved: bool, reason: str | None = None) -> None: ...
