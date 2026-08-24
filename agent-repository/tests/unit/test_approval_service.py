"""Approval service tests (plan milestone M5.2 Definition of done)."""

import pytest

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.control_plane.approval_matrix import MANDATORY_APPROVAL_ACTIONS
from agent_platform.control_plane.approval_service import ApprovalService


class MutableClock:
    def __init__(self, start: str = "2026-08-24T09:00:00Z"):
        self._now = start

    def now_iso(self) -> str:
        return self._now

    def advance_seconds(self, seconds: int) -> None:
        from datetime import datetime, timedelta

        dt = datetime.fromisoformat(self._now.replace("Z", "+00:00"))
        self._now = (dt + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _service(*, ttl=None, clock=None):
    return ApprovalService(
        id_generator=SequentialIdGenerator(),
        clock=clock or FixedClock(),
        approval_ttl_seconds=ttl,
    )


@pytest.mark.parametrize("action", sorted(MANDATORY_APPROVAL_ACTIONS))
def test_each_mandatory_action_requires_approval(action):
    service = _service()
    assert service.requires_approval(action) is True
    assert service.is_approved(action) is False  # not approved by default


def test_ordinary_action_does_not_require_approval():
    service = _service()
    assert service.requires_approval("repository.read") is False
    assert service.is_approved("repository.read") is True


def test_approval_lifecycle():
    service = _service()
    request = service.request("production_change", "SPOC-1")
    assert service.get_status(request.approval_id) == "pending"

    service.resolve(request.approval_id, approved=True)
    assert service.get_status(request.approval_id) == "approved"
    assert service.is_approved("production_change", "SPOC-1") is True


def test_rejected_approval_does_not_count():
    service = _service()
    request = service.request("access_expansion", "SPOC-1")
    service.resolve(request.approval_id, approved=False)
    assert service.is_approved("access_expansion", "SPOC-1") is False


def test_expired_approval_blocks_and_cannot_be_approved():
    clock = MutableClock()
    service = _service(ttl=60, clock=clock)
    request = service.request("policy_exception", "SPOC-1")
    assert service.get_status(request.approval_id) == "pending"

    clock.advance_seconds(61)
    assert service.get_status(request.approval_id) == "expired"
    assert service.is_approved("policy_exception", "SPOC-1") is False

    # Approving an expired request must not flip it to approved.
    service.resolve(request.approval_id, approved=True)
    assert service.get_status(request.approval_id) == "expired"
    assert service.is_approved("policy_exception", "SPOC-1") is False
