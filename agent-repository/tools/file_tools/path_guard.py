"""Path security kernel (masterplan section 14.4, plan milestone M4.1).

Enforces, independently of any prompt:

- canonicalization of every path;
- rejection of paths outside the mounted roots;
- rejection of symbolic-link escapes;
- separation of read vs. write permission per a manifest-derived allowlist.

Every rejection raises a typed exception with a stable, machine-readable
``code`` so callers and audit logs can distinguish the failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PathSecurityError(Exception):
    code = "PATH_SECURITY"


class PathOutsideRootError(PathSecurityError):
    code = "PATH_OUTSIDE_ROOT"


class SymlinkEscapeError(PathSecurityError):
    code = "SYMLINK_ESCAPE"


class PermissionDeniedError(PathSecurityError):
    code = "PERMISSION_DENIED"


@dataclass(frozen=True)
class PathGuard:
    """Guards file access against a set of mounted roots and an
    allowlist mapping an absolute path (or directory prefix) to ``read``
    or ``write`` permission."""

    mount_roots: tuple[Path, ...]
    allowlist: dict[str, str]  # absolute path string -> "read" | "write"

    def __post_init__(self) -> None:
        roots = tuple(Path(r).resolve() for r in self.mount_roots)
        object.__setattr__(self, "mount_roots", roots)

    # -- public API ---------------------------------------------------

    def assert_read(self, path: Path | str) -> Path:
        """Return the canonical resolved path if reading is permitted,
        otherwise raise a typed ``PathSecurityError``."""
        resolved = self._canonicalize(path)
        self._assert_within_roots(resolved)
        if not self._has_permission(resolved, "read"):
            raise PermissionDeniedError(
                f"no read permission for '{resolved}' under allowlist {sorted(self.allowlist)}"
            )
        return resolved

    def assert_write(self, path: Path | str) -> Path:
        """Return the canonical resolved path if writing is permitted,
        otherwise raise a typed ``PathSecurityError``."""
        resolved = self._canonicalize(path)
        self._assert_within_roots(resolved)
        if not self._has_permission(resolved, "write"):
            raise PermissionDeniedError(
                f"no write permission for '{resolved}' under allowlist {sorted(self.allowlist)}"
            )
        return resolved

    # -- internals ------------------------------------------------------

    def _canonicalize(self, path: Path | str) -> Path:
        abs_path = Path(path).absolute()
        self._assert_no_symlink_escape(abs_path)
        return abs_path.resolve()

    def _assert_no_symlink_escape(self, abs_path: Path) -> None:
        """Walk each path component; if a component is a symlink, its
        resolved target must remain inside a mount root. Distinguishes a
        symlink escape from a plain `..` traversal so each gets its own
        error code."""
        parts = abs_path.parts
        if not parts:
            return
        current = Path(parts[0])
        for part in parts[1:]:
            current = current / part
            if current.is_symlink():
                target = current.resolve()
                if not self._within_roots(target):
                    raise SymlinkEscapeError(
                        f"symlink '{current}' resolves to '{target}' outside mounted roots"
                    )

    def _assert_within_roots(self, resolved: Path) -> None:
        if not self._within_roots(resolved):
            raise PathOutsideRootError(
                f"'{resolved}' is outside mounted roots {list(self.mount_roots)}"
            )

    def _within_roots(self, resolved: Path) -> bool:
        return any(resolved == root or root in resolved.parents for root in self.mount_roots)

    def _has_permission(self, resolved: Path, required: str) -> bool:
        resolved_str = resolved.as_posix()
        # Exact match first, then ancestor-directory prefixes (longest
        # prefix wins so a more specific rule overrides a broader one).
        candidates = [
            key
            for key in self.allowlist
            if resolved_str == key or resolved_str.startswith(key.rstrip("/") + "/")
        ]
        if not candidates:
            return False
        best = max(candidates, key=len)
        granted = self.allowlist[best]
        return granted == "write" or (granted == "read" and required == "read")
