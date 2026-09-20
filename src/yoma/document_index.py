"""SQLite-backed document metadata, content index, and retrieval queries."""

from datetime import datetime, timezone
import re
import sqlite3

from .documents import DocumentInput, ExtractionResult, source_metadata


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_document(
    connection: sqlite3.Connection,
    document: DocumentInput,
    user_id: int,
    workspace_root_id: int,
    extraction: ExtractionResult,
    status: str = "extracted",
) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO documents (
            document_id, user_id, workspace_root_id, canonical_path, relative_path,
            filename, extension, size, modified_at, content_type, extraction_status,
            extracted_text, extracted_at, parser_name, parser_version, source_metadata_json,
            indexed_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            user_id = excluded.user_id,
            workspace_root_id = excluded.workspace_root_id,
            canonical_path = excluded.canonical_path,
            relative_path = excluded.relative_path,
            filename = excluded.filename,
            extension = excluded.extension,
            size = excluded.size,
            modified_at = excluded.modified_at,
            content_type = excluded.content_type,
            extraction_status = excluded.extraction_status,
            extracted_text = excluded.extracted_text,
            extracted_at = excluded.extracted_at,
            parser_name = excluded.parser_name,
            parser_version = excluded.parser_version,
            source_metadata_json = excluded.source_metadata_json,
            indexed_at = excluded.indexed_at,
            updated_at = excluded.updated_at
        """,
        (
            document.document_id,
            user_id,
            workspace_root_id,
            str(document.canonical_path),
            document.relative_path,
            document.filename,
            document.extension,
            document.size,
            document.modified_at,
            document.content_type,
            status,
            extraction.text,
            now,
            extraction.parser_name,
            extraction.parser_version,
            source_metadata(extraction),
            now,
            now,
            now,
        ),
    )
    connection.execute("DELETE FROM document_index WHERE document_id = ?", (document.document_id,))
    connection.execute(
        "INSERT INTO document_index (document_id, user_id, workspace_root_id, relative_path, content) VALUES (?, ?, ?, ?, ?)",
        (document.document_id, user_id, workspace_root_id, document.relative_path, extraction.text),
    )
    if _fts_available(connection):
        connection.execute("DELETE FROM document_fts WHERE document_id = ?", (document.document_id,))
        connection.execute(
            "INSERT INTO document_fts (document_id, user_id, workspace_root_id, relative_path, content) VALUES (?, ?, ?, ?, ?)",
            (document.document_id, user_id, workspace_root_id, document.relative_path, extraction.text),
        )


def record_failed_document(
    connection: sqlite3.Connection,
    document: DocumentInput,
    user_id: int,
    workspace_root_id: int,
    status: str,
) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO documents (
            document_id, user_id, workspace_root_id, canonical_path, relative_path,
            filename, extension, size, modified_at, content_type, extraction_status,
            extracted_text, extracted_at, parser_name, parser_version, source_metadata_json,
            indexed_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, 'none', 'none', '[]', NULL, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            size = excluded.size,
            modified_at = excluded.modified_at,
            extraction_status = excluded.extraction_status,
            extracted_text = '',
            extracted_at = excluded.extracted_at,
            parser_name = 'none',
            parser_version = 'none',
            source_metadata_json = '[]',
            indexed_at = NULL,
            updated_at = excluded.updated_at
        """,
        (
            document.document_id,
            user_id,
            workspace_root_id,
            str(document.canonical_path),
            document.relative_path,
            document.filename,
            document.extension,
            document.size,
            document.modified_at,
            document.content_type,
            status,
            now,
            now,
            now,
        ),
    )
    connection.execute("DELETE FROM document_index WHERE document_id = ?", (document.document_id,))
    if _fts_available(connection):
        connection.execute("DELETE FROM document_fts WHERE document_id = ?", (document.document_id,))


def _fts_available(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'document_fts'"
    ).fetchone() is not None


def search_documents(connection: sqlite3.Connection, user_id: int, query: str, limit: int) -> list[sqlite3.Row]:
    terms = re.findall(r"[\w-]+", query, flags=re.UNICODE)
    if not terms:
        return []
    bounded_limit = max(1, min(limit, 100))
    if _fts_available(connection):
        match_query = " AND ".join(f'"{term}"' for term in terms)
        try:
            return connection.execute(
                """
                SELECT d.*, r.canonical_path AS approved_root_path FROM document_fts f
                JOIN documents d ON d.document_id = f.document_id
                JOIN workspace_roots r ON r.id = d.workspace_root_id AND r.user_id = d.user_id
                WHERE f.user_id = ? AND f MATCH ?
                ORDER BY d.updated_at DESC LIMIT ?
                """,
                (user_id, match_query, bounded_limit),
            ).fetchall()
        except sqlite3.OperationalError:
            pass
    like_query = "%" + "%".join(terms) + "%"
    return connection.execute(
        "SELECT d.*, r.canonical_path AS approved_root_path FROM documents d JOIN workspace_roots r ON r.id = d.workspace_root_id AND r.user_id = d.user_id WHERE d.user_id = ? AND lower(d.extracted_text) LIKE lower(?) ORDER BY d.updated_at DESC LIMIT ?",
        (user_id, like_query, bounded_limit),
    ).fetchall()
