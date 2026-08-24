from pathlib import Path

import pytest

from agent_platform.schemas.canonicalize import (
    FrontMatterError,
    compute_content_hash,
    parse_okf_text,
    split_front_matter,
    verify_content_hash,
)


def test_split_front_matter_basic():
    text = "---\nid: X\n---\nbody text\n"
    front_matter, body = split_front_matter(text)
    assert front_matter.strip() == "id: X"
    assert body.strip() == "body text"


def test_split_front_matter_requires_leading_delimiter():
    with pytest.raises(FrontMatterError):
        split_front_matter("# no front matter here\n")


def test_split_front_matter_requires_closing_delimiter():
    with pytest.raises(FrontMatterError):
        split_front_matter("---\nid: X\nbody without closing delimiter\n")


def test_parse_okf_text_roundtrip():
    text = "---\nid: OKF-1\ntype: concept\n---\n# Hello\n"
    doc = parse_okf_text(text)
    assert doc.id == "OKF-1"
    assert doc.type == "concept"
    assert doc.body.strip() == "# Hello"


def test_content_hash_is_deterministic():
    front_matter = {"id": "OKF-1", "type": "concept", "tags": ["b", "a"]}
    body = "Some body text.\n"
    hash1 = compute_content_hash(front_matter, body)
    hash2 = compute_content_hash(front_matter, body)
    assert hash1 == hash2
    assert hash1.startswith("sha256:")


def test_content_hash_excludes_itself_from_input():
    front_matter_without_hash = {"id": "OKF-1", "type": "concept"}
    front_matter_with_hash = dict(front_matter_without_hash, content_hash="sha256:deadbeef")
    body = "Body.\n"
    assert compute_content_hash(front_matter_without_hash, body) == compute_content_hash(
        front_matter_with_hash, body
    )


def test_content_hash_changes_when_content_changes():
    body = "Body.\n"
    hash_a = compute_content_hash({"id": "A"}, body)
    hash_b = compute_content_hash({"id": "B"}, body)
    assert hash_a != hash_b


def test_verify_content_hash_true_when_absent():
    doc = parse_okf_text("---\nid: OKF-1\n---\nbody\n")
    assert verify_content_hash(doc) is True


def test_verify_content_hash_detects_mismatch():
    front_matter = {"id": "OKF-1", "content_hash": "sha256:not-the-real-hash"}
    text = "---\nid: OKF-1\ncontent_hash: sha256:not-the-real-hash\n---\nbody\n"
    doc = parse_okf_text(text)
    assert doc.front_matter == front_matter
    assert verify_content_hash(doc) is False


def test_verify_content_hash_detects_match():
    body = "body\n"
    correct_hash = compute_content_hash({"id": "OKF-1"}, body)
    text = f"---\nid: OKF-1\ncontent_hash: {correct_hash}\n---\n{body}"
    doc = parse_okf_text(text)
    assert verify_content_hash(doc) is True
