"""Structured audit recording without secrets or raw document content."""

import json
from datetime import datetime, timezone
import sqlite3


def record(connection: sqlite3.Connection, event_type: str, username: str | None, details: dict) -> None:
    connection.execute(
        "INSERT INTO audit_events (event_type, username, details_json, created_at) VALUES (?, ?, ?, ?)",
        (event_type, username, json.dumps(details, sort_keys=True), datetime.now(timezone.utc).isoformat()),
    )
    connection.commit()

