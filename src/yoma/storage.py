"""Approved-root filesystem validation."""

from pathlib import Path


def approved_path(candidate: str, approved_roots: tuple[Path, ...]) -> Path:
    path = Path(candidate).expanduser().resolve(strict=False)
    for root in approved_roots:
        root = root.expanduser().resolve(strict=False)
        try:
            path.relative_to(root)
            return path
        except ValueError:
            continue
    raise PermissionError("path is outside configured approved roots")
