from pathlib import Path

import pytest

from yoma.storage import approved_path


def test_approved_path_rejects_outside_root(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        approved_path(str(tmp_path.parent / "outside.txt"), (tmp_path,))


def test_approved_path_resolves_inside_root(tmp_path: Path) -> None:
    assert approved_path(str(tmp_path / "nested" / "file.txt"), (tmp_path,)) == (tmp_path / "nested" / "file.txt").resolve()


def test_approved_path_blocks_traversal_and_similar_sibling_roots(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    sibling = tmp_path / "approved-other"
    assert approved_path(str(root / "nested" / ".." / "file.txt"), (root,)) == (root / "file.txt").resolve()
    with pytest.raises(PermissionError):
        approved_path(str(root / "nested" / ".." / ".." / "outside.txt"), (root,))
    with pytest.raises(PermissionError):
        approved_path(str(sibling / "file.txt"), (root,))


def test_approved_path_canonicalizes_relative_root(tmp_path: Path) -> None:
    root = tmp_path / "approved"
    assert approved_path(str(root / "file.txt"), (Path(str(root)),)) == (root / "file.txt").resolve()
