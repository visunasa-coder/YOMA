"""User-owned, bounded persistent memory operations."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import sqlite3
import uuid


CATEGORIES = frozenset({"preference", "fact", "goal", "instruction", "project", "context"})
_SECRET_PATTERN = re.compile(r"(?i)(?:password|api[_ -]?key|bearer\s+token|access[_ -]?token)\s*[:=]")


class MemoryError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class MemorySource:
    memory_id: str
    category: str
    source: str
    importance: int
    content: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_category(category: str) -> str:
    if not isinstance(category, str) or category not in CATEGORIES:
        raise MemoryError("invalid_category", "memory category is invalid")
    return category


def validate_content(content: str, max_length: int) -> str:
    if not isinstance(content, str) or not content.strip():
        raise MemoryError("invalid_content", "memory content is required")
    if len(content) > max_length:
        raise MemoryError("content_too_long", "memory content exceeds the configured limit")
    if _SECRET_PATTERN.search(content):
        raise MemoryError("secret_rejected", "memory content must not contain credentials")
    return content.strip()


def validate_source(source: str) -> str:
    if not isinstance(source, str) or not source.strip() or len(source.strip()) > 200:
        raise MemoryError("invalid_source", "memory source is invalid")
    return source.strip()


def validate_importance(importance: int) -> int:
    if isinstance(importance, bool) or not isinstance(importance, int) or not 1 <= importance <= 5:
        raise MemoryError("invalid_importance", "importance must be between 1 and 5")
    return importance


def validate_expiration(expires_at: str | None) -> str | None:
    if expires_at is None:
        return None
    if not isinstance(expires_at, str):
        raise MemoryError("invalid_expiration", "expiration must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError as exc:
        raise MemoryError("invalid_expiration", "expiration must be an ISO timestamp") from exc


def validate_metadata(metadata: dict | None) -> str:
    if metadata is None:
        return "{}"
    if not isinstance(metadata, dict):
        raise MemoryError("invalid_metadata", "metadata must be an object")
    serialized = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
    if _SECRET_PATTERN.search(serialized):
        raise MemoryError("secret_rejected", "memory metadata must not contain credentials")
    return serialized


def is_active_clause() -> str:
    return "(expires_at IS NULL OR expires_at > ?)"


def row_to_source(row) -> MemorySource:
    return MemorySource(row["id"], row["category"], row["source"], row["importance"], row["content"])


def search_memories(connection: sqlite3.Connection, user_id: int, query: str, limit: int, max_query_length: int) -> list[MemorySource]:
    if not isinstance(query, str) or not query.strip():
        raise MemoryError("empty_query", "memory search query must not be empty")
    normalized = query.strip()
    if len(normalized) > max_query_length:
        raise MemoryError("query_too_long", "memory search query exceeds the configured limit")
    bounded_limit = max(1, limit)
    escaped = normalized.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    rows = connection.execute(
        f"SELECT id, category, content, source, importance FROM memories WHERE user_id = ? AND {is_active_clause()} AND (content LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\' OR source LIKE ? ESCAPE '\\') ORDER BY importance DESC, updated_at DESC, id LIMIT ?",
        (user_id, now_iso(), pattern, pattern, pattern, bounded_limit),
    ).fetchall()
    return [row_to_source(row) for row in rows]


def context_memories(connection: sqlite3.Connection, user_id: int, query: str, limit: int, max_query_length: int) -> list[MemorySource]:
    if not query.strip():
        return []
    return search_memories(connection, user_id, query, limit, max_query_length)


def new_memory_id() -> str:
    return uuid.uuid4().hex
