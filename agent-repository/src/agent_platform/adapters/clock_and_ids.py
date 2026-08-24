"""Clock and IdGenerator adapters (plan section 20.1)."""

from __future__ import annotations

import itertools
from datetime import datetime, timezone


class SystemClock:
    def now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FixedClock:
    """Deterministic clock for tests."""

    def __init__(self, fixed_iso: str = "2026-08-24T09:00:00Z") -> None:
        self._fixed_iso = fixed_iso

    def now_iso(self) -> str:
        return self._fixed_iso


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        import uuid

        return f"{prefix}_{uuid.uuid4().hex[:16]}"


class SequentialIdGenerator:
    """Deterministic id generator for tests: `<prefix>_000001`,
    `<prefix>_000002`, ... per prefix."""

    def __init__(self) -> None:
        self._counters: dict[str, itertools.count] = {}

    def new_id(self, prefix: str) -> str:
        counter = self._counters.setdefault(prefix, itertools.count(1))
        return f"{prefix}_{next(counter):06d}"
