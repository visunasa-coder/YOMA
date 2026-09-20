from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from yoma.db import connection_scope
from yoma.office.operations import OperationalEvent


class OperationalEventPersistence:
    """Durable SQLite persistence for normalized YOMA operational events."""

    def __init__(self, db_path: str | Path) -> None:
        if not str(db_path).strip():
            raise ValueError("db_path is required")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with connection_scope(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_operational_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    organization_id TEXT,
                    user_id TEXT,
                    system_id TEXT,
                    source TEXT,
                    location_id TEXT,
                    severity TEXT NOT NULL,
                    data_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_events_occurred_at
                ON yoma_operational_events(occurred_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_events_organization
                ON yoma_operational_events(organization_id, occurred_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_events_user
                ON yoma_operational_events(user_id, occurred_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_events_system
                ON yoma_operational_events(system_id, occurred_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_events_type
                ON yoma_operational_events(event_type, occurred_at)
                """
            )

            connection.commit()

    @staticmethod
    def _validate_event(event: OperationalEvent) -> None:
        if not isinstance(event, OperationalEvent):
            raise TypeError("event must be an OperationalEvent")

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if not isinstance(value, datetime):
            raise TypeError("occurred_at must be a datetime")
        return value.isoformat()

    @staticmethod
    def _row_to_event(row: Any) -> OperationalEvent:
        return OperationalEvent(
            event_id=str(row["event_id"]),
            event_type=str(row["event_type"]),
            occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
            organization_id=row["organization_id"],
            user_id=row["user_id"],
            system_id=row["system_id"],
            source=row["source"],
            location_id=row["location_id"],
            severity=str(row["severity"]),
            data=json.loads(row["data_json"]),
        )

    def save(self, event: OperationalEvent) -> bool:
        """Persist one event.

        Returns True when a new event was inserted and False when the
        event_id already exists.
        """
        self._validate_event(event)

        with connection_scope(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO yoma_operational_events (
                    event_id,
                    event_type,
                    occurred_at,
                    organization_id,
                    user_id,
                    system_id,
                    source,
                    location_id,
                    severity,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    self._timestamp(event.occurred_at),
                    event.organization_id,
                    event.user_id,
                    event.system_id,
                    event.source,
                    event.location_id,
                    event.severity,
                    json.dumps(
                        event.data,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            )
            connection.commit()
            return cursor.rowcount == 1

    def save_many(self, events: list[OperationalEvent]) -> int:
        """Persist multiple events and return the number newly inserted."""
        if not isinstance(events, list):
            raise TypeError("events must be a list")

        for event in events:
            self._validate_event(event)

        inserted = 0

        with connection_scope(self.db_path) as connection:
            for event in events:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO yoma_operational_events (
                        event_id,
                        event_type,
                        occurred_at,
                        organization_id,
                        user_id,
                        system_id,
                        source,
                        location_id,
                        severity,
                        data_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.event_type,
                        self._timestamp(event.occurred_at),
                        event.organization_id,
                        event.user_id,
                        event.system_id,
                        event.source,
                        event.location_id,
                        event.severity,
                        json.dumps(
                            event.data,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ),
                )
                inserted += cursor.rowcount

            connection.commit()

        return inserted

    def get(self, event_id: str) -> OperationalEvent | None:
        event_id = str(event_id).strip()

        if not event_id:
            raise ValueError("event_id is required")

        with connection_scope(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    event_id,
                    event_type,
                    occurred_at,
                    organization_id,
                    user_id,
                    system_id,
                    source,
                    location_id,
                    severity,
                    data_json
                FROM yoma_operational_events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()

        return self._row_to_event(row) if row is not None else None

    def load_all(self) -> list[OperationalEvent]:
        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id,
                    event_type,
                    occurred_at,
                    organization_id,
                    user_id,
                    system_id,
                    source,
                    location_id,
                    severity,
                    data_json
                FROM yoma_operational_events
                ORDER BY occurred_at ASC, event_id ASC
                """
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def count(self) -> int:
        with connection_scope(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM yoma_operational_events"
            ).fetchone()

        return int(row[0])

    def by_type(self, event_type: str) -> list[OperationalEvent]:
        event_type = str(event_type).strip()

        if not event_type:
            raise ValueError("event_type is required")

        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id,
                    event_type,
                    occurred_at,
                    organization_id,
                    user_id,
                    system_id,
                    source,
                    location_id,
                    severity,
                    data_json
                FROM yoma_operational_events
                WHERE event_type = ?
                ORDER BY occurred_at ASC, event_id ASC
                """,
                (event_type,),
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def by_organization(self, organization_id: str) -> list[OperationalEvent]:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id is required")

        return self._by_dimension("organization_id", organization_id)

    def by_user(self, user_id: str) -> list[OperationalEvent]:
        user_id = str(user_id).strip()

        if not user_id:
            raise ValueError("user_id is required")

        return self._by_dimension("user_id", user_id)

    def by_system(self, system_id: str) -> list[OperationalEvent]:
        system_id = str(system_id).strip()

        if not system_id:
            raise ValueError("system_id is required")

        return self._by_dimension("system_id", system_id)

    def _by_dimension(
        self,
        column: str,
        value: str,
    ) -> list[OperationalEvent]:
        allowed_columns = {
            "organization_id",
            "user_id",
            "system_id",
        }

        if column not in allowed_columns:
            raise ValueError("unsupported dimension")

        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    event_id,
                    event_type,
                    occurred_at,
                    organization_id,
                    user_id,
                    system_id,
                    source,
                    location_id,
                    severity,
                    data_json
                FROM yoma_operational_events
                WHERE {column} = ?
                ORDER BY occurred_at ASC, event_id ASC
                """,
                (value,),
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[OperationalEvent]:
        if not isinstance(start, datetime):
            raise TypeError("start must be a datetime")

        if not isinstance(end, datetime):
            raise TypeError("end must be a datetime")

        if start > end:
            raise ValueError("start must not be after end")

        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id,
                    event_type,
                    occurred_at,
                    organization_id,
                    user_id,
                    system_id,
                    source,
                    location_id,
                    severity,
                    data_json
                FROM yoma_operational_events
                WHERE occurred_at >= ?
                  AND occurred_at <= ?
                ORDER BY occurred_at ASC, event_id ASC
                """,
                (
                    self._timestamp(start),
                    self._timestamp(end),
                ),
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def clear(self) -> None:
        with connection_scope(self.db_path) as connection:
            connection.execute(
                "DELETE FROM yoma_operational_events"
            )
            connection.commit()
