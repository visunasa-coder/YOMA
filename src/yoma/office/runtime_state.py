from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RuntimeStatePersistence:
    """Persistent storage for the current YOMA embedded runtime state."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_runtime_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_runtime_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(self, *, state: str, reason: str) -> None:
        if not state:
            raise ValueError("Runtime state is required")
        if not reason:
            raise ValueError("Runtime state reason is required")

        updated_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO yoma_runtime_state (
                    id,
                    state,
                    reason,
                    updated_at
                )
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (state, reason, updated_at),
            )

            conn.execute(
                """
                INSERT INTO yoma_runtime_state_history (
                    state,
                    reason,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (state, reason, updated_at),
            )

    def load(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT state, reason, updated_at
                FROM yoma_runtime_state
                WHERE id = 1
                """
            ).fetchone()

        if row is None:
            return None

        return {
            "state": row[0],
            "reason": row[1],
            "updated_at": row[2],
        }

    def history(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT state, reason, updated_at
                FROM yoma_runtime_state_history
                ORDER BY id ASC
                """
            ).fetchall()

        return [
            {
                "state": row[0],
                "reason": row[1],
                "updated_at": row[2],
            }
            for row in rows
        ]

    def recovery_metadata(self) -> dict[str, Any]:
        record = self.load()

        if record is None:
            return {
                "recovery_required": False,
                "previous_state": None,
                "previous_reason": None,
                "previous_updated_at": None,
            }

        previous_state = record["state"]

        return {
            "recovery_required": previous_state in {"running", "failed"},
            "previous_state": previous_state,
            "previous_reason": record["reason"],
            "previous_updated_at": record["updated_at"],
        }

    def startup_diagnostics(self) -> dict[str, Any]:
        recovery = self.recovery_metadata()

        if recovery["recovery_required"]:
            previous_state = recovery["previous_state"]

            if previous_state == "running":
                message = (
                    "Recovery may be required because the previous "
                    "runtime ended while marked running."
                )
            else:
                message = (
                    "Recovery may be required because the previous "
                    "runtime ended in a failed state."
                )
        elif recovery["previous_state"] == "stopped":
            message = "Previous runtime shutdown completed cleanly."
        else:
            message = "No previous runtime state was found."

        return {
            **recovery,
            "message": message,
        }

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM yoma_runtime_state WHERE id = 1"
            )
