from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from yoma.db import connection_scope
from yoma.office.operations import OperationalSignal


class OperationalSignalPersistence:
    """Durable SQLite persistence for YOMA operational signals."""

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
                CREATE TABLE IF NOT EXISTS yoma_operational_signals (
                    signal_id TEXT PRIMARY KEY,
                    signal_type TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    organization_id TEXT,
                    user_id TEXT,
                    system_id TEXT,
                    score REAL NOT NULL,
                    severity TEXT NOT NULL,
                    evidence_event_ids_json TEXT NOT NULL DEFAULT '[]',
                    data_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_signals_detected_at
                ON yoma_operational_signals(detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_signals_type
                ON yoma_operational_signals(signal_type, detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_signals_organization
                ON yoma_operational_signals(organization_id, detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_signals_user
                ON yoma_operational_signals(user_id, detected_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_yoma_operational_signals_system
                ON yoma_operational_signals(system_id, detected_at)
                """
            )

            connection.commit()

    @staticmethod
    def _validate_signal(signal: OperationalSignal) -> None:
        if not isinstance(signal, OperationalSignal):
            raise TypeError("signal must be an OperationalSignal")

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if not isinstance(value, datetime):
            raise TypeError("detected_at must be a datetime")
        return value.isoformat()

    @staticmethod
    def _row_to_signal(row: Any) -> OperationalSignal:
        evidence = json.loads(row["evidence_event_ids_json"])
        data = json.loads(row["data_json"])

        return OperationalSignal(
            signal_id=str(row["signal_id"]),
            signal_type=str(row["signal_type"]),
            detected_at=datetime.fromisoformat(str(row["detected_at"])),
            organization_id=row["organization_id"],
            user_id=row["user_id"],
            system_id=row["system_id"],
            score=float(row["score"]),
            severity=str(row["severity"]),
            evidence_event_ids=tuple(str(item) for item in evidence),
            data=data,
        )

    @staticmethod
    def _serialize_evidence(signal: OperationalSignal) -> str:
        return json.dumps(
            list(signal.evidence_event_ids),
            sort_keys=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _serialize_data(signal: OperationalSignal) -> str:
        return json.dumps(
            signal.data,
            sort_keys=True,
            separators=(",", ":"),
        )

    def save(self, signal: OperationalSignal) -> bool:
        """Persist one signal.

        Returns True when inserted and False when signal_id already exists.
        """
        self._validate_signal(signal)

        with connection_scope(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO yoma_operational_signals (
                    signal_id,
                    signal_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    score,
                    severity,
                    evidence_event_ids_json,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.signal_id,
                    signal.signal_type,
                    self._timestamp(signal.detected_at),
                    signal.organization_id,
                    signal.user_id,
                    signal.system_id,
                    float(signal.score),
                    signal.severity,
                    self._serialize_evidence(signal),
                    self._serialize_data(signal),
                ),
            )
            connection.commit()
            return cursor.rowcount == 1

    def save_many(self, signals: list[OperationalSignal]) -> int:
        """Persist multiple signals and return the number newly inserted."""
        if not isinstance(signals, list):
            raise TypeError("signals must be a list")

        for signal in signals:
            self._validate_signal(signal)

        inserted = 0

        with connection_scope(self.db_path) as connection:
            for signal in signals:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO yoma_operational_signals (
                        signal_id,
                        signal_type,
                        detected_at,
                        organization_id,
                        user_id,
                        system_id,
                        score,
                        severity,
                        evidence_event_ids_json,
                        data_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.signal_id,
                        signal.signal_type,
                        self._timestamp(signal.detected_at),
                        signal.organization_id,
                        signal.user_id,
                        signal.system_id,
                        float(signal.score),
                        signal.severity,
                        self._serialize_evidence(signal),
                        self._serialize_data(signal),
                    ),
                )
                inserted += cursor.rowcount

            connection.commit()

        return inserted

    def get(self, signal_id: str) -> OperationalSignal | None:
        signal_id = str(signal_id).strip()

        if not signal_id:
            raise ValueError("signal_id is required")

        with connection_scope(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    signal_id,
                    signal_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    score,
                    severity,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_signals
                WHERE signal_id = ?
                """,
                (signal_id,),
            ).fetchone()

        return self._row_to_signal(row) if row is not None else None

    def load_all(self) -> list[OperationalSignal]:
        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    signal_id,
                    signal_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    score,
                    severity,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_signals
                ORDER BY detected_at ASC, signal_id ASC
                """
            ).fetchall()

        return [self._row_to_signal(row) for row in rows]

    def count(self) -> int:
        with connection_scope(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM yoma_operational_signals"
            ).fetchone()

        return int(row[0])

    def by_type(self, signal_type: str) -> list[OperationalSignal]:
        signal_type = str(signal_type).strip()

        if not signal_type:
            raise ValueError("signal_type is required")

        return self._by_dimension("signal_type", signal_type)

    def by_organization(
        self,
        organization_id: str,
    ) -> list[OperationalSignal]:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id is required")

        return self._by_dimension("organization_id", organization_id)

    def by_user(self, user_id: str) -> list[OperationalSignal]:
        user_id = str(user_id).strip()

        if not user_id:
            raise ValueError("user_id is required")

        return self._by_dimension("user_id", user_id)

    def by_system(self, system_id: str) -> list[OperationalSignal]:
        system_id = str(system_id).strip()

        if not system_id:
            raise ValueError("system_id is required")

        return self._by_dimension("system_id", system_id)

    def _by_dimension(
        self,
        column: str,
        value: str,
    ) -> list[OperationalSignal]:
        allowed_columns = {
            "signal_type",
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
                    signal_id,
                    signal_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    score,
                    severity,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_signals
                WHERE {column} = ?
                ORDER BY detected_at ASC, signal_id ASC
                """,
                (value,),
            ).fetchall()

        return [self._row_to_signal(row) for row in rows]

    def between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[OperationalSignal]:
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
                    signal_id,
                    signal_type,
                    detected_at,
                    organization_id,
                    user_id,
                    system_id,
                    score,
                    severity,
                    evidence_event_ids_json,
                    data_json
                FROM yoma_operational_signals
                WHERE detected_at >= ?
                  AND detected_at <= ?
                ORDER BY detected_at ASC, signal_id ASC
                """,
                (
                    self._timestamp(start),
                    self._timestamp(end),
                ),
            ).fetchall()

        return [self._row_to_signal(row) for row in rows]

    def by_evidence_event(
        self,
        event_id: str,
    ) -> list[OperationalSignal]:
        """Return signals whose persisted evidence contains event_id."""
        event_id = str(event_id).strip()

        if not event_id:
            raise ValueError("event_id is required")

        signals = self.load_all()

        return [
            signal
            for signal in signals
            if event_id in signal.evidence_event_ids
        ]

    def clear(self) -> None:
        with connection_scope(self.db_path) as connection:
            connection.execute(
                "DELETE FROM yoma_operational_signals"
            )
            connection.commit()
