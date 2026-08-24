"""Path security kernel test corpus (plan milestone M4.1 Definition of
done)."""

import pytest

from tools.file_tools.path_guard import (
    PathGuard,
    PathOutsideRootError,
    PermissionDeniedError,
    SymlinkEscapeError,
)


@pytest.fixture
def root(tmp_path):
    return tmp_path / "root"


def test_traversal_outside_root_is_rejected(root):
    root.mkdir()
    guard = PathGuard(mount_roots=(root,), allowlist={str(root): "write"})
    with pytest.raises(PathOutsideRootError):
        guard.assert_read(root / ".." / ".." / "etc" / "passwd")


def test_symlink_escape_is_rejected_with_specific_code(root, tmp_path):
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = root / "link"
    link.symlink_to(outside)

    guard = PathGuard(mount_roots=(root,), allowlist={str(root): "write"})
    with pytest.raises(SymlinkEscapeError) as exc_info:
        guard.assert_read(link)
    assert exc_info.value.code == "SYMLINK_ESCAPE"


def test_write_to_read_only_path_is_rejected(root):
    root.mkdir()
    target = root / "f.txt"
    target.write_text("x")
    guard = PathGuard(mount_roots=(root,), allowlist={str(target): "read"})
    with pytest.raises(PermissionDeniedError) as exc_info:
        guard.assert_write(target)
    assert exc_info.value.code == "PERMISSION_DENIED"


def test_read_and_write_within_allowed_root_succeed(root):
    root.mkdir()
    target = root / "g.txt"
    target.write_text("hello")
    guard = PathGuard(mount_roots=(root,), allowlist={str(root): "write"})
    assert guard.assert_read(target) == target.resolve()
    assert guard.assert_write(target) == target.resolve()


def test_longest_prefix_rule_wins(root):
    root.mkdir()
    subdir = root / "sub"
    subdir.mkdir()
    target = subdir / "h.txt"
    target.write_text("x")
    guard = PathGuard(
        mount_roots=(root,),
        allowlist={str(root): "write", str(subdir): "read"},
    )
    # The more specific subdir rule (read) overrides the broader root (write).
    with pytest.raises(PermissionDeniedError):
        guard.assert_write(target)
    assert guard.assert_read(target) == target.resolve()
