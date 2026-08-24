"""Scoped read/write tool tests (plan milestone M4.2 Definition of done)."""

import threading

import pytest

from tools.file_tools.path_guard import PathGuard
from tools.file_tools.repository_read import read_bytes
from tools.file_tools.repository_write_scoped import SecretRejectionError, write_bytes


def _guard(root, perm="write"):
    return PathGuard(mount_roots=(root,), allowlist={str(root): perm})


def test_read_returns_content_and_emits_audit(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("hello")
    events = []
    content = read_bytes(target, _guard(tmp_path), audit=events.append)
    assert content == b"hello"
    assert any(e["event"] == "repository_read" for e in events)


def test_write_rejects_secret_and_logs_security_event(tmp_path):
    target = tmp_path / "b.txt"
    events = []
    with pytest.raises(SecretRejectionError):
        write_bytes(
            target,
            b"AWS_ACCESS_KEY_ID=AKIA0123456789ABCDEF\n",
            _guard(tmp_path),
            audit=events.append,
        )
    assert not target.exists()  # nothing was written
    assert any(e["event"] == "security_event" for e in events)


def test_write_is_atomic_and_audited(tmp_path):
    target = tmp_path / "c.txt"
    events = []
    content_hash = write_bytes(target, b"content", _guard(tmp_path), audit=events.append)
    assert target.read_bytes() == b"content"
    assert content_hash.startswith("sha256:")
    writes = [e for e in events if e["event"] == "repository_write"]
    assert len(writes) == 1
    assert writes[0]["after_hash"] == content_hash


def test_concurrent_writes_are_serialized_without_data_loss(tmp_path):
    target = tmp_path / "d.txt"
    guard = _guard(tmp_path)
    payload_a = b"A" * 50000
    payload_b = b"B" * 50000

    def worker(payload: bytes, count: int) -> None:
        for _ in range(count):
            write_bytes(target, payload, guard)

    threads = [
        threading.Thread(target=worker, args=(payload_a, 20)),
        threading.Thread(target=worker, args=(payload_b, 20)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = target.read_bytes()
    # No interleaving or partial write: the final content is exactly one
    # of the two complete payloads.
    assert final in (payload_a, payload_b)
