"""Bounded, local execution for the explicitly registered M7 tools."""

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path, PureWindowsPath

from .workspace import WorkspacePathError, discover_files, validate_child, validate_root


class ToolExecutionError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ToolLimits:
    max_read_size: int
    max_write_size: int
    max_files: int
    max_directory_depth: int


TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def _argument(arguments: dict, name: str, expected_type: type):
    value = arguments.get(name)
    if expected_type is int and isinstance(value, bool):
        value = None
    if not isinstance(value, expected_type):
        raise ToolExecutionError("invalid_arguments", f"{name} is required")
    return value


def _relative_path(arguments: dict) -> str:
    value = _argument(arguments, "relative_path", str)
    if not value.strip() or "\x00" in value:
        raise ToolExecutionError("invalid_path", "relative_path is invalid")
    if Path(value).is_absolute() or PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive:
        raise ToolExecutionError("path_denied", "path must be relative to the approved root")
    return value


def _reject_reparse_components(candidate: Path, root: Path) -> None:
    """Reject links/reparse points in the target path, including internal links."""
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ToolExecutionError("path_denied", "path is outside the approved root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if current.is_symlink() or (os.name == "nt" and getattr(current.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400):
                raise ToolExecutionError("path_denied", "links and reparse points are not supported")
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ToolExecutionError("filesystem_error", "path could not be inspected") from exc


def _root(connection, user_id: int, arguments: dict) -> tuple[int, Path]:
    root_id = _argument(arguments, "workspace_root_id", int)
    row = connection.execute("SELECT id, canonical_path FROM workspace_roots WHERE id = ? AND user_id = ?", (root_id, user_id)).fetchone()
    if row is None:
        raise ToolExecutionError("root_not_found", "approved root not found")
    try:
        root = validate_root(row["canonical_path"])
    except WorkspacePathError as exc:
        raise ToolExecutionError("root_unavailable", "approved root is unavailable") from exc
    return root_id, root


def _target(root: Path, arguments: dict) -> tuple[str, Path]:
    relative = _relative_path(arguments)
    try:
        target = validate_child(root / relative, root)
    except WorkspacePathError as exc:
        raise ToolExecutionError("path_denied", str(exc)) from exc
    _reject_reparse_components(target, root)
    return relative, target


def _metadata(root_id: int, root: Path, path: Path) -> dict:
    try:
        stat = path.stat()
        if not path.is_file():
            raise ToolExecutionError("invalid_target", "target is not a file")
        return {
            "workspace_root_id": root_id,
            "relative_path": path.relative_to(root).as_posix(),
            "filename": path.name,
            "extension": path.suffix,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
    except ToolExecutionError:
        raise
    except FileNotFoundError as exc:
        raise ToolExecutionError("not_found", "file not found") from exc
    except OSError as exc:
        raise ToolExecutionError("filesystem_error", "file metadata is unavailable") from exc


def execute_tool(tool_name: str, arguments: dict, connection, user_id: int, limits: ToolLimits) -> dict | list[dict]:
    if tool_name == "workspace.list_files":
        root_id, root = _root(connection, user_id, arguments)
        try:
            files = discover_files(root, max_file_size=limits.max_read_size)
        except (WorkspacePathError, OSError) as exc:
            raise ToolExecutionError("filesystem_error", "approved root could not be listed") from exc
        return [{"workspace_root_id": root_id, **file.__dict__} for file in files[:limits.max_files]]

    root_id, root = _root(connection, user_id, arguments)
    relative, target = _target(root, arguments)
    if tool_name == "workspace.file_info":
        return _metadata(root_id, root, target)
    if tool_name == "workspace.read_text":
        if target.suffix.casefold() not in TEXT_EXTENSIONS:
            raise ToolExecutionError("unsupported_operation", "only approved text extensions may be read")
        try:
            data = target.read_bytes()
            if len(data) > limits.max_read_size:
                raise ToolExecutionError("size_limit", "file exceeds the read limit")
            return {**_metadata(root_id, root, target), "content": data.decode("utf-8")}
        except UnicodeDecodeError as exc:
            raise ToolExecutionError("unsupported_operation", "file is not valid UTF-8 text") from exc
        except FileNotFoundError as exc:
            raise ToolExecutionError("not_found", "file not found") from exc
        except PermissionError as exc:
            raise ToolExecutionError("filesystem_error", "file is inaccessible") from exc
    if tool_name == "workspace.write_text":
        content = _argument(arguments, "content", str)
        if target.suffix.casefold() not in TEXT_EXTENSIONS:
            raise ToolExecutionError("unsupported_operation", "only approved text extensions may be written")
        if len(content.encode("utf-8")) > limits.max_write_size:
            raise ToolExecutionError("size_limit", "content exceeds the write limit")
        if target.exists():
            raise ToolExecutionError("overwrite_denied", "existing files cannot be overwritten")
        if not target.parent.exists() or not target.parent.is_dir():
            raise ToolExecutionError("not_found", "parent directory not found")
        try:
            with target.open("x", encoding="utf-8", newline="") as handle:
                handle.write(content)
        except FileExistsError as exc:
            raise ToolExecutionError("overwrite_denied", "existing files cannot be overwritten") from exc
        except OSError as exc:
            raise ToolExecutionError("filesystem_error", "file could not be created") from exc
        return {"workspace_root_id": root_id, "relative_path": relative, "size": len(content.encode("utf-8"))}
    if tool_name == "workspace.create_directory":
        depth = len(target.relative_to(root).parts)
        if depth < 1 or depth > limits.max_directory_depth:
            raise ToolExecutionError("size_limit", "directory depth exceeds the configured limit")
        if target.exists():
            raise ToolExecutionError("already_exists", "directory already exists")
        try:
            target.mkdir(parents=False)
        except FileNotFoundError as exc:
            raise ToolExecutionError("not_found", "parent directory not found") from exc
        except OSError as exc:
            raise ToolExecutionError("filesystem_error", "directory could not be created") from exc
        return {"workspace_root_id": root_id, "relative_path": relative}
    raise ToolExecutionError("unknown_tool", "tool is not registered")
