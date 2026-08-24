"""Scoped write tool (masterplan section 14.4, plan milestone M4.2).

Implements atomic writes, an inter-process file lock, before/after
hashing, secret scanning on staged content, and per-call audit events.

A write is rejected if secret scanning flags the content; the rejection
is itself logged as a security event (M4.2 Definition of done).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Optional

from tools.file_tools.path_guard import PathGuard
from tools.file_tools.secret_scanner import has_secrets, scan_bytes


class SecretRejectionError(Exception):
    code = "SECRET_REJECTED"


def write_bytes(
    path: Path | str,
    content: bytes,
    path_guard: PathGuard,
    *,
    audit: Optional[Callable[[dict], None]] = None,
    lock_dir: Optional[Path] = None,
    attribution: Optional[dict] = None,
) -> str:
    """Atomically write `content` to `path` after a write-permission
    check, secret scan, and file lock acquisition. Returns the content
    hash of the written bytes.

    ``attribution`` is merged into every emitted audit event so a file
    mutation is always attributable to a specific actor/tool/run
    (masterplan section 14.4 "record every read and write event"; plan
    milestone M4.5).

    Raises ``SecretRejectionError`` if a secret is detected; the rejection
    is emitted through ``audit`` as a ``security_event`` before raising.
    """
    resolved = path_guard.assert_write(path)
    attribution = attribution or {}

    # Secret scan BEFORE any bytes touch disk (masterplan section 14.4).
    findings = scan_bytes(content)
    if findings:
        if audit is not None:
            audit(
                {
                    "event": "security_event",
                    "severity": "critical",
                    "reason": "secret_rejected",
                    "path": resolved.as_posix(),
                    "rules": sorted({f.rule for f in findings}),
                    **attribution,
                }
            )
        raise SecretRejectionError(
            f"write to '{resolved}' rejected: {len(findings)} secret finding(s) "
            f"({sorted({f.rule for f in findings})})"
        )

    before_hash = _sha256_file(resolved)
    new_hash = "sha256:" + hashlib.sha256(content).hexdigest()

    _locked_write(resolved, content, lock_dir=lock_dir)

    after_hash = _sha256_file(resolved)

    if audit is not None:
        audit(
            {
                "event": "repository_write",
                "path": resolved.as_posix(),
                "before_hash": before_hash,
                "after_hash": after_hash,
                "content_hash": new_hash,
                "size_bytes": len(content),
                **attribution,
            }
        )

    return new_hash


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _locked_write(resolved: Path, content: bytes, *, lock_dir: Path | None) -> None:
    """Serialized, atomic write: acquire an advisory lock on a sidecar
    lock file, write to a temporary file in the same directory, then
    atomically ``os.replace`` it over the target."""
    import fcntl

    lock_path = (lock_dir or resolved.parent) / (resolved.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        tmp_path = resolved.with_name(resolved.name + f".tmp-{os.getpid()}")
        tmp_path.write_bytes(content)
        os.replace(tmp_path, resolved)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
