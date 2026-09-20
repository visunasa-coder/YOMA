from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from yoma.db import connection_scope
from yoma.office.operations import OperationalSituation


class OperationalSituationPersistence:
    """Durable SQLite persistence for YOMA operational situations."""

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
                CREATE TABLE IF NOT EXISTS yoma_operational_situations (
                    situation_id TEXT PRIMARY KEY,
                    situation_type TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    organization_id TEXT,
                    user_id TEXT,
                    system_id TEXT,
                    severity TEXT NOT NULL,
                    score REAL NOT NULL,
                    signal_ids_json TEXT NOT NULL DEFAULT '[]',
                    evidence_event_ids_json TEXT NOT NULL DEFAULT '[]',
                    data_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_situations_detected_at
                ON yoma_operational_situations(detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_situations_type
                ON yoma_operational_situations(situation_type, detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_situations_organization
                ON yoma_operational_situations(organization_id, detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_situations_user
                ON yoma_operational_situations(user_id, detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_situations_system
                ON yoma_operational_situations(system_id, detected_at)
                """
            )

            connection.commit()

    @staticmethod
    def _validate_situation(
        situation: OperationalSituation,
    ) -> None:
        if not isinstance(situation, OperationalSituation):
            raise TypeError(
                "situation must be an OperationalSituation"
            )

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if not isinstance(value, datetime):
            raise TypeError("detected_at must be a datetime")
        return value.isoformat()

    @staticmethod
    def _serialize_ids(values: tuple[str, ...]) -> str:
        return json.dumps(
            list(values),
            sort_keys=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _serialize_data(data: dict) -> str:
        return json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _row_to_situation(row: Any) -> OperationalSituation:
        signal_ids = json.loads(row["signal_ids_json"])
        evidence_event_ids = json.loads(
            row["evidence_event_ids_json"]
        )
        data = json.loads(row["data_json"])

        return OperationalSituation(
            situation_id=str(row["situation_id"]),
            situation_type=str(row["situation_type"]),
            detected_at=datetime.fromisoformat(
                str(row["detected_at"])
            ),
            organization_id=row["organization_id"],
            user_id=row["user_id"],
            system_id=row["system_id"],
            severity=str(row["severity"]),
            score=float(row["score"]),
            signal_ids=tuple(str(item) for item in signal_ids),
            evidence_event_ids=tuple(
                str(item) for item in evidence_event_ids
            ),
            data=data,
        )

    def save(self, situation: OperationalSituation) -> bool:
        """Persist one situation.

        Returns True when inserted and False when situation_id already
        exists.
        """
        self._validate_situation(situation)

        with connection_scope(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO yoma_operational_situations (
                    situation_id,
                    situation_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    severity,
                    score,
                    signal_ids_json,
                    evidence_event_ids_json,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    situation.situation_id,
                    situation.situation_type,
                    self._timestamp(situation.detected_at),
                    situation.organization_id,
                    situation.user_id,
                    situation.system_id,
                    situation.severity,
                    float(situation.score),
                    self._serialize_ids(situation.signal_ids),
                    self._serialize_ids(
                        situation.evidence_event_ids
                    ),
                    self._serialize_data(situation.data),
                ),
            )
            connection.commit()
            return cursor.rowcount == 1

    def save_many(
        self,
        situations: list[OperationalSituation],
    ) -> int:
        """Persist multiple situations and return newly inserted count."""
        if not isinstance(situations, list):
            raise TypeError("situations must be a list")

        for situation in situations:
            self._validate_situation(situation)

        inserted = 0

        with connection_scope(self.db_path) as connection:
            for situation in situations:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO yoma_operational_situations (
                        situation_id,
                        situation_type,
                        detected_at,
                        organization_id,
                        user_id,
                        system_id,
                        severity,
                        score,
                        signal_ids_json,
                        evidence_event_ids_json,
                        data_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        situation.situation_id,
                        situation.situation_type,
                        self._timestamp(situation.detected_at),
                        situation.organization_id,
                        situation.user_id,
                        situation.system_id,
                        situation.severity,
                        float(situation.score),
                        self._serialize_ids(situation.signal_ids),
                        self._serialize_ids(
                            situation.evidence_event_ids
                        ),
                        self._serialize_data(situation.data),
                    ),
                )
                inserted += cursor.rowcount

            connection.commit()

        return inserted

    def get(
        self,
        situation_id: str,
    ) -> OperationalSituation | None:
        situation_id = str(situation_id).strip()

        if not situation_id:
            raise ValueError("situation_id is required")

        with connection_scope(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    situation_id,
                    situation_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    severity,
                    score,
                    signal_ids_json,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_situations
                WHERE situation_id = ?
                """,
                (situation_id,),
            ).fetchone()

        return (
            self._row_to_situation(row)
            if row is not None
            else None
        )

    def load_all(self) -> list[OperationalSituation]:
        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    situation_id,
                    situation_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    severity,
                    score,
                    signal_ids_json,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_situations
                ORDER BY detected_at ASC, situation_id ASC
                """
            ).fetchall()

        return [
            self._row_to_situation(row)
            for row in rows
        ]

    def count(self) -> int:
        with connection_scope(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM yoma_operational_situations
                """
            ).fetchone()

        return int(row[0])

    def by_type(
        self,
        situation_type: str,
    ) -> list[OperationalSituation]:
        situation_type = str(situation_type).strip()

        if not situation_type:
            raise ValueError("situation_type is required")

        return self._by_dimension(
            "situation_type",
            situation_type,
        )

    def by_organization(
        self,
        organization_id: str,
    ) -> list[OperationalSituation]:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id is required")

        return self._by_dimension(
            "organization_id",
            organization_id,
        )

    def by_user(
        self,
        user_id: str,
    ) -> list[OperationalSituation]:
        user_id = str(user_id).strip()

        if not user_id:
            raise ValueError("user_id is required")

        return self._by_dimension("user_id", user_id)

    def by_system(
        self,
        system_id: str,
    ) -> list[OperationalSituation]:
        system_id = str(system_id).strip()

        if not system_id:
            raise ValueError("system_id is required")

        return self._by_dimension("system_id", system_id)

    def _by_dimension(
        self,
        column: str,
        value: str,
    ) -> list[OperationalSituation]:
        allowed_columns = {
            "situation_type",
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
                    situation_id,
                    situation_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    severity,
                    score,
                    signal_ids_json,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_situations
                WHERE {column} = ?
                ORDER BY detected_at ASC, situation_id ASC
                """,
                (value,),
            ).fetchall()

        return [
            self._row_to_situation(row)
            for row in rows
        ]

    def by_signal(
        self,
        signal_id: str,
    ) -> list[OperationalSituation]:
        """Return situations containing the supplied signal ID."""
        signal_id = str(signal_id).strip()

        if not signal_id:
            raise ValueError("signal_id is required")

        return [
            situation
            for situation in self.load_all()
            if signal_id in situation.signal_ids
        ]

    def by_evidence_event(
        self,
        event_id: str,
    ) -> list[OperationalSituation]:
        """Return situations containing the supplied event ID."""
        event_id = str(event_id).strip()

        if not event_id:
            raise ValueError("event_id is required")

        return [
            situation
            for situation in self.load_all()
            if event_id in situation.evidence_event_ids
        ]

    def between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[OperationalSituation]:
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
                    situation_id,
                    situation_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    severity,
                    score,
                    signal_ids_json,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_situations
                WHERE detected_at >= ?
                  AND detected_at <= ?
                ORDER BY detected_at ASC, situation_id ASC
                """,
                (
                    self._timestamp(start),
                    self._timestamp(end),
                ),
            ).fetchall()

        return [
            self._row_to_situation(row)
            for row in rows
        ]

    def clear(self) -> None:
        with connection_scope(self.db_path) as connection:
            connection.execute(
                "DELETE FROM yoma_operational_situations"
            )
            connection.commit()
