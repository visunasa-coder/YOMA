from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_events import OrganizationChangeEvent


class OrganizationChangeEventPersistence:
    """SQLite persistence and replay for YOMA organization change events."""

    def __init__(self, db_path: str | Path) -> None:
        if not str(db_path).strip():
            raise ValueError("db_path is required")

        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_organization_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    previous_state_json TEXT,
                    current_state_json TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    timestamp TEXT NOT NULL,
                    UNIQUE (
                        event_type,
                        entity_type,
                        entity_id,
                        timestamp
                    )
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_organization_events_type
                ON yoma_organization_events(event_type)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_organization_events_entity
                ON yoma_organization_events(
                    entity_type,
                    entity_id
                )
                """
            )

    def save(
        self,
        event: OrganizationChangeEvent,
    ) -> None:
        if not isinstance(
            event,
            OrganizationChangeEvent,
        ):
            raise TypeError(
                "event must be an OrganizationChangeEvent"
            )

        previous_state = (
            json.dumps(event.previous_state)
            if event.previous_state is not None
            else None
        )

        current_state = (
            json.dumps(event.current_state)
            if event.current_state is not None
            else None
        )

        metadata = json.dumps(event.metadata)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO yoma_organization_events (
                    event_type,
                    entity_type,
                    entity_id,
                    previous_state_json,
                    current_state_json,
                    metadata_json,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_type,
                    event.entity_type,
                    event.entity_id,
                    previous_state,
                    current_state,
                    metadata,
                    event.timestamp,
                ),
            )

    def _row_to_event(
        self,
        row: tuple[Any, ...],
    ) -> OrganizationChangeEvent:
        (
            event_type,
            entity_type,
            entity_id,
            previous_state_json,
            current_state_json,
            metadata_json,
            timestamp,
        ) = row

        previous_state = (
            json.loads(previous_state_json)
            if previous_state_json is not None
            else None
        )

        current_state = (
            json.loads(current_state_json)
            if current_state_json is not None
            else None
        )

        metadata = json.loads(metadata_json)

        return OrganizationChangeEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_state=previous_state,
            current_state=current_state,
            metadata=metadata,
            timestamp=timestamp,
        )

    def load_all(self) -> list[OrganizationChangeEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_type,
                    entity_type,
                    entity_id,
                    previous_state_json,
                    current_state_json,
                    metadata_json,
                    timestamp
                FROM yoma_organization_events
                ORDER BY id ASC
                """
            ).fetchall()

        return [
            self._row_to_event(row)
            for row in rows
        ]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM yoma_organization_events
                """
            ).fetchone()

        return int(row[0])

    def by_type(
        self,
        event_type: str,
    ) -> list[OrganizationChangeEvent]:
        event_type = str(event_type).strip()

        if not event_type:
            raise ValueError(
                "event_type is required"
            )

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_type,
                    entity_type,
                    entity_id,
                    previous_state_json,
                    current_state_json,
                    metadata_json,
                    timestamp
                FROM yoma_organization_events
                WHERE event_type = ?
                ORDER BY id ASC
                """,
                (event_type,),
            ).fetchall()

        return [
            self._row_to_event(row)
            for row in rows
        ]

    def by_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[OrganizationChangeEvent]:
        entity_type = str(entity_type).strip()
        entity_id = str(entity_id).strip()

        if not entity_type:
            raise ValueError(
                "entity_type is required"
            )

        if not entity_id:
            raise ValueError(
                "entity_id is required"
            )

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_type,
                    entity_type,
                    entity_id,
                    previous_state_json,
                    current_state_json,
                    metadata_json,
                    timestamp
                FROM yoma_organization_events
                WHERE entity_type = ?
                  AND entity_id = ?
                ORDER BY id ASC
                """,
                (
                    entity_type,
                    entity_id,
                ),
            ).fetchall()

        return [
            self._row_to_event(row)
            for row in rows
        ]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM yoma_organization_events
                """
            )

    def replay(
        self,
        event_bus: OrganizationEventBus,
    ) -> int:
        if not isinstance(
            event_bus,
            OrganizationEventBus,
        ):
            raise TypeError(
                "event_bus must be an OrganizationEventBus"
            )

        events = self.load_all()

        return event_bus.publish_many(events)