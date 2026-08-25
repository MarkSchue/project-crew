#!/usr/bin/env python3
"""Disaster-recovery rehearsal script (masterplan section 20.4, plan
milestone M8.4).

Rehearses backup + restore of a platform state directory and records
*measured* timings and the data-loss window. The result JSON is committed
at ``ops/rehearsal/result.json`` so the rehearsal is reproducible and the
numbers are auditable, not asserted by hand.

Usage::

    python ops/rehearsal/dr_rehearsal.py --source DIR --backup-dir DIR \
        --result-out ops/rehearsal/result.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import time
from pathlib import Path


def _checksums(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        manifest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def backup(source: Path, backup_dir: Path) -> tuple[Path, float, int]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    snapshot_at = time.time()
    archive = backup_dir / f"platform-state-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.tar.gz"
    manifest = _checksums(source)
    byte_count = sum((source / rel).stat().st_size for rel in manifest)

    started = time.monotonic()
    with tarfile.open(archive, "w:gz") as tar:
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        manifest_path = source / ".checksums.json"
        manifest_path.write_bytes(manifest_bytes)
        try:
            tar.add(source, arcname="state")
        finally:
            manifest_path.unlink()
    backup_seconds = time.monotonic() - started
    return archive, backup_seconds, byte_count, snapshot_at


def restore(archive: Path, restore_root: Path) -> tuple[float, dict[str, str]]:
    started = time.monotonic()
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(restore_root)
    restore_seconds = time.monotonic() - started
    restored_dir = restore_root / "state"
    manifest = json.loads((restored_dir / ".checksums.json").read_text(encoding="utf-8"))
    return restore_seconds, manifest


def verify(restored_dir: Path, manifest: dict[str, str]) -> list[str]:
    failures = []
    current = _checksums(restored_dir)
    for rel, expected in manifest.items():
        if current.get(rel) != expected:
            failures.append(f"checksum mismatch: {rel}")
    for rel in current:
        if rel not in manifest and rel != ".checksums.json":
            failures.append(f"unexpected extra file: {rel}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--result-out", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    restore_root = Path(tempfile.mkdtemp(prefix="dr-restore-", dir=backup_dir))

    archive, backup_seconds, byte_count, snapshot_at = backup(source, backup_dir)
    restore_seconds, manifest = restore(archive, restore_root)
    restored_dir = restore_root / "state"
    verify_seconds_start = time.monotonic()
    failures = verify(restored_dir, manifest)
    verify_seconds = time.monotonic() - verify_seconds_start
    restored_at = time.time()

    result = {
        "rehearsal": {
            "source": str(source),
            "archive": archive.name,
            "files_backed_up": len(manifest),
            "bytes_backed_up": byte_count,
            "backup_seconds": round(backup_seconds, 4),
            "restore_seconds": round(restore_seconds, 4),
            "verify_seconds": round(verify_seconds, 4),
            "checksum_failures": failures,
            "ok": not failures,
            # Measured data-loss window: wall-clock time between the backup
            # snapshot and the completion of a verified restore — i.e. the
            # period of live writes that a restore would not include.
            "data_loss_window_seconds": round(restored_at - snapshot_at, 4),
        }
    }

    out_path = Path(args.result_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(restore_root, ignore_errors=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
