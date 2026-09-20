"""Authorized retrieval from the local indexed document store."""

from dataclasses import dataclass
import json
import sqlite3

from .document_index import search_documents
from .workspace import WorkspacePathError, validate_child, validate_root


class RetrievalError(ValueError):
    """Safe retrieval request failure."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RetrievalSource:
    document_id: str
    filename: str
    relative_path: str
    workspace_root_id: int
    excerpt: str
    rank: int
    source_locations: tuple[dict, ...]


def validate_query(query: str, max_length: int = 1000) -> str:
    if not isinstance(query, str) or not query.strip():
        raise RetrievalError("query must not be empty", "empty_query")
    normalized = query.strip()
    if len(normalized) > max_length:
        raise RetrievalError("query exceeds the configured length limit", "query_too_long")
    return normalized


def retrieve(
    connection: sqlite3.Connection,
    user_id: int,
    query: str,
    limit: int = 10,
    max_query_length: int = 1000,
) -> list[RetrievalSource]:
    normalized_query = validate_query(query, max_query_length)
    if limit < 1:
        raise RetrievalError("result limit must be positive", "invalid_limit")
    rows = search_documents(connection, user_id, normalized_query, limit)
    sources: list[RetrievalSource] = []
    for rank, row in enumerate(rows, start=1):
        try:
            root_path = row["approved_root_path"]
            validate_child(row["canonical_path"], validate_root(root_path))
            locations = tuple(json.loads(row["source_metadata_json"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError, WorkspacePathError):
            continue
        sources.append(
            RetrievalSource(
                document_id=row["document_id"],
                filename=row["filename"],
                relative_path=row["relative_path"],
                workspace_root_id=row["workspace_root_id"],
                excerpt=row["extracted_text"][:2000],
                rank=rank,
                source_locations=locations,
            )
        )
    return sources

