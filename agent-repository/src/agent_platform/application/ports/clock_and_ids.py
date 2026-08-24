"""Clock and IdGenerator ports (plan section 20.1).

Injected everywhere a timestamp or a new identifier is needed so that
tests can supply deterministic implementations instead of depending on
wall-clock time or randomness.
"""

from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    def now_iso(self) -> str: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...
