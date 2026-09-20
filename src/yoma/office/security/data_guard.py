"""Defensive guards around sensitive file and database operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class DataGuardResult:
    allowed: bool
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class FileGuard:
    """Restricts processing to explicitly permitted file classes."""

    DEFAULT_EXTENSIONS = frozenset({
        ".txt",
        ".csv",
        ".json",
        ".xml",
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".png",
        ".jpg",
        ".jpeg",
        ".wav",
    })

    def __init__(
        self,
        *,
        allowed_extensions=None,
        max_size_bytes: int = 25 * 1024 * 1024,
    ) -> None:
        self.allowed_extensions = frozenset(
            allowed_extensions or self.DEFAULT_EXTENSIONS
        )
        self.max_size_bytes = max_size_bytes

    def inspect(
        self,
        *,
        filename: str,
        size_bytes: int,
    ) -> DataGuardResult:
        if not filename.strip():
            return DataGuardResult(False, "filename required")

        if size_bytes < 0:
            return DataGuardResult(False, "invalid file size")

        if size_bytes > self.max_size_bytes:
            return DataGuardResult(False, "file exceeds size limit")

        extension = Path(filename).suffix.lower()

        if extension not in self.allowed_extensions:
            return DataGuardResult(False, "file type not permitted")

        if "\x00" in filename:
            return DataGuardResult(False, "invalid filename")

        return DataGuardResult(True, "file accepted")


class DatabaseGuard:
    """Blocks arbitrary SQL and requires explicit operation scopes."""

    _WRITE_RE = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|ATTACH|DETACH)\b",
        re.IGNORECASE,
    )

    def inspect(
        self,
        *,
        operation: str,
        scope: str,
        approved: bool = False,
    ) -> DataGuardResult:

        operation = operation.strip().lower()
        scope = scope.strip()

        if not scope:
            return DataGuardResult(False, "database scope required")

        if operation not in {"read", "write"}:
            return DataGuardResult(False, "unsupported database operation")

        if operation == "write" and not approved:
            return DataGuardResult(
                False,
                "database write requires explicit governed approval",
            )

        return DataGuardResult(
            True,
            f"database {operation} permitted for explicit scope",
        )

    def inspect_sql(self, sql: str) -> DataGuardResult:
        if not isinstance(sql, str) or not sql.strip():
            return DataGuardResult(False, "SQL statement required")

        if self._WRITE_RE.search(sql):
            return DataGuardResult(
                False,
                "raw write or schema-changing SQL is prohibited",
            )

        return DataGuardResult(
            True,
            "read-only SQL pattern accepted for downstream parameterized validation",
        )
