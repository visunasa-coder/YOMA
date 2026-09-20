"""Safe, read-only filesystem operations for explicitly approved roots."""

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import stat


MAX_DISCOVERY_FILE_SIZE = 100 * 1024 * 1024


class WorkspacePathError(ValueError):
    """Raised when a workspace path is invalid or outside its approved root."""


@dataclass(frozen=True)
class DiscoveredFile:
    relative_path: str
    filename: str
    extension: str
    size: int
    modified_at: str


def canonicalize_path(candidate: str | Path) -> Path:
    if not isinstance(candidate, (str, Path)) or not str(candidate).strip():
        raise WorkspacePathError("path must be a non-empty string")
    try:
        return Path(candidate).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise WorkspacePathError("path could not be canonicalized") from exc


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_root(candidate: str | Path) -> Path:
    root = canonicalize_path(candidate)
    try:
        if not root.exists() or not root.is_dir():
            raise WorkspacePathError("approved root must be an existing directory")
    except OSError as exc:
        raise WorkspacePathError("approved root is inaccessible") from exc
    return root


def validate_child(candidate: str | Path, root: str | Path) -> Path:
    canonical_root = canonicalize_path(root)
    canonical_candidate = canonicalize_path(candidate)
    if not is_within(canonical_candidate, canonical_root):
        raise WorkspacePathError("path is outside the approved root")
    return canonical_candidate


def _is_reparse_point(path: Path, entry: os.DirEntry[str]) -> bool:
    if entry.is_symlink():
        return True
    attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return os.name == "nt" and bool(attributes & reparse_flag)


def discover_files(root: str | Path, max_file_size: int = MAX_DISCOVERY_FILE_SIZE) -> list[DiscoveredFile]:
    """Recursively discover metadata without following links or reading content."""
    canonical_root = validate_root(root)
    if max_file_size < 0:
        raise ValueError("max_file_size must not be negative")

    discovered: list[DiscoveredFile] = []
    pending = [canonical_root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except (OSError, PermissionError):
            if current == canonical_root:
                raise WorkspacePathError("approved root is inaccessible")
            continue

        for entry in entries:
            entry_path = Path(entry.path)
            try:
                if _is_reparse_point(entry_path, entry):
                    continue
                canonical_entry = entry_path.resolve(strict=False)
                if not is_within(canonical_entry, canonical_root):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(canonical_entry)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                metadata = entry.stat(follow_symlinks=False)
                if metadata.st_size > max_file_size:
                    continue
                relative_path = canonical_entry.relative_to(canonical_root).as_posix()
                discovered.append(
                    DiscoveredFile(
                        relative_path=relative_path,
                        filename=entry.name,
                        extension=Path(entry.name).suffix,
                        size=metadata.st_size,
                        modified_at=datetime.fromtimestamp(metadata.st_mtime, timezone.utc).isoformat(),
                    )
                )
            except (OSError, PermissionError, RuntimeError, ValueError):
                continue

    return sorted(discovered, key=lambda item: item.relative_path.casefold())

