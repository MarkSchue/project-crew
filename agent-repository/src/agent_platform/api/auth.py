"""Dev identity provider and RBAC helpers (plan milestone M6.1/M6.5).

The MVP uses a development identity provider: bearer tokens map directly
to pre-registered ``Identity`` records. Production OIDC/OAuth (masterplan
section 15.2, M6.1 "even if pointed at a dev identity provider") swaps in
behind the same ``authenticate(token) -> Identity`` seam, so RBAC does not
change.

RBAC rule: a ``human`` identity scoped to ``project_id`` may access only
that project's resources. A platform admin (``roles`` containing
``admin``) bypasses the project-scope check.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Identity:
    actor_type: str  # "human" | "agent" | "system"
    actor_id: str
    project_id: str | None  # None => platform admin
    roles: frozenset[str] = field(default_factory=frozenset)

    def is_admin(self) -> bool:
        return "admin" in self.roles

    def can_access_project(self, project_id: str) -> bool:
        return self.is_admin() or self.project_id == project_id


class DevAuthProvider:
    def __init__(self, identities: dict[str, Identity] | None = None) -> None:
        self._identities = dict(identities or {})

    def register(self, token: str, identity: Identity) -> None:
        self._identities[token] = identity

    def authenticate(self, token: str) -> Identity | None:
        return self._identities.get(token)


def dev_token(project_id: str, *, role: str = "member") -> str:
    """Convenience for tests/CLI: a deterministic dev token encoding the
    project scope. Not a security boundary — the dev provider is a
    stand-in for a real identity provider."""
    return f"dev-token-{project_id}-{role}"
