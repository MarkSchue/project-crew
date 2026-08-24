"""Scoped read tool (masterplan section 14.4, plan milestone M4.2).

Reads a file only through the ``PathGuard`` and records a read audit
event. Returns the raw bytes plus the file's content hash so callers can
verify provenance without trusting the path alone.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Optional

from tools.file_tools.path_guard import PathGuard


def read_bytes(
    path: Path | str,
    path_guard: PathGuard,
    *,
    audit: Optional[Callable[[dict], None]] = None,
    attribution: Optional[dict] = None,
) -> bytes:
    """Read `path` after a read-permission check. Returns file bytes.

    ``audit``, if provided, is called with a single dict describing the
    read; ``attribution`` (actor/tool/run) is merged into it so reads are
    attributable too (masterplan section 14.4).
    """
    resolved = path_guard.assert_read(path)
    content = resolved.read_bytes()

    if audit is not None:
        audit(
            {
                "event": "repository_read",
                "path": resolved.as_posix(),
                "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                **(attribution or {}),
            }
        )

    return content
