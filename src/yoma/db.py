"""SQLite connection and schema management."""

from pathlib import Path
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    username TEXT,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_roots (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    canonical_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, canonical_path)
);
CREATE INDEX IF NOT EXISTS idx_workspace_roots_user_id ON workspace_roots(user_id);
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    workspace_root_id INTEGER NOT NULL REFERENCES workspace_roots(id),
    canonical_path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    size INTEGER NOT NULL,
    modified_at TEXT NOT NULL,
    content_type TEXT NOT NULL,
    extraction_status TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    extracted_at TEXT,
    parser_name TEXT,
    parser_version TEXT,
    source_metadata_json TEXT NOT NULL,
    indexed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, workspace_root_id, canonical_path)
);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_root_id ON documents(workspace_root_id);
CREATE TABLE IF NOT EXISTS document_index (
    document_id TEXT PRIMARY KEY REFERENCES documents(document_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    workspace_root_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_document_index_user_id ON document_index(user_id);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id, id);
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    importance INTEGER NOT NULL CHECK (importance BETWEEN 1 AND 5),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_category ON memories(user_id, category);
CREATE INDEX IF NOT EXISTS idx_memories_user_expiration ON memories(user_id, expires_at);
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'awaiting_approval', 'running', 'completed', 'failed', 'cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    current_step INTEGER NOT NULL DEFAULT 0,
    max_steps INTEGER NOT NULL,
    approval_required INTEGER NOT NULL CHECK (approval_required IN (0, 1)),
    cancellation_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancellation_requested IN (0, 1)),
    failure_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id, updated_at);
CREATE TABLE IF NOT EXISTS agent_steps (
    id INTEGER PRIMARY KEY,
    agent_run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_index INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    tool_name TEXT,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'completed', 'failed', 'cancelled')),
    result_metadata_json TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    failure_reason TEXT,
    UNIQUE (agent_run_id, step_index)
);
CREATE INDEX IF NOT EXISTS idx_agent_steps_run_id ON agent_steps(agent_run_id, step_index);
CREATE TABLE IF NOT EXISTS integration_connections (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    integration_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('connected', 'disconnected', 'expired', 'unavailable')),
    granted_scopes_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_used_at TEXT,
    expires_at TEXT,
    UNIQUE (user_id, integration_id)
);
CREATE INDEX IF NOT EXISTS idx_integration_connections_user ON integration_connections(user_id, integration_id);

CREATE TABLE IF NOT EXISTS yoma_integrations (
    integration_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    category TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    configured INTEGER NOT NULL DEFAULT 0 CHECK (configured IN (0, 1)),
    configuration_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'unconfigured',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_yoma_integrations_provider
    ON yoma_integrations(provider);
CREATE INDEX IF NOT EXISTS idx_yoma_integrations_category
    ON yoma_integrations(category);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection_scope(path: Path) -> Iterator[sqlite3.Connection]:
    """Yield one connection to one operation, then always release it."""
    connection = connect(path)
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path: Path) -> None:
    """Create the schema during application setup in a short-lived transaction."""
    with connection_scope(path) as connection:
        connection.executescript(SCHEMA)
        try:
            connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(document_id UNINDEXED, user_id UNINDEXED, workspace_root_id UNINDEXED, relative_path UNINDEXED, content)"
            )
        except sqlite3.OperationalError:
            # The document_index table remains the deterministic LIKE-search fallback.
            pass
        connection.commit()


def health_check(path: Path) -> bool:
    """Check the local database using a short-lived request-safe connection."""
    try:
        with connection_scope(path) as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except (OSError, sqlite3.Error):
        return False
