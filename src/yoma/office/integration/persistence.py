from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yoma.db import connection_scope
from yoma.office.integration.model import Integration


class IntegrationPersistence:
    """Persistent storage for provider-neutral YOMA integrations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _integration_id(
        self,
        integration: Integration,
        connection: Any,
    ) -> str:
        row = connection.execute(
            """
            SELECT integration_id
            FROM yoma_integrations
            WHERE name = ?
            """,
            (integration.name,),
        ).fetchone()

        if row is not None:
            return str(row["integration_id"])

        return str(uuid.uuid4())

    def save(self, integration: Integration) -> None:
        now = self._now()
        status = integration.status()

        with connection_scope(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO yoma_integrations (
                    integration_id,
                    name,
                    provider,
                    category,
                    enabled,
                    configured,
                    configuration_json,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    provider = excluded.provider,
                    category = excluded.category,
                    enabled = excluded.enabled,
                    configured = excluded.configured,
                    configuration_json = excluded.configuration_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    self._integration_id(integration, connection),
                    integration.name,
                    integration.provider,
                    integration.category,
                    int(integration.enabled),
                    int(integration.configured),
                    json.dumps(
                        integration.configuration(),
                        sort_keys=True,
                    ),
                    status.health.get("status", "unknown"),
                    now,
                    now,
                ),
            )
            connection.commit()

    def load_all(self) -> list[dict[str, Any]]:
        with connection_scope(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    integration_id,
                    name,
                    provider,
                    category,
                    enabled,
                    configured,
                    configuration_json,
                    status,
                    created_at,
                    updated_at
                FROM yoma_integrations
                ORDER BY name
                """
            ).fetchall()

        results: list[dict[str, Any]] = []

        for row in rows:
            try:
                configuration = json.loads(row["configuration_json"])
            except (TypeError, json.JSONDecodeError):
                configuration = {}

            results.append(
                {
                    "integration_id": row["integration_id"],
                    "name": row["name"],
                    "provider": row["provider"],
                    "category": row["category"],
                    "enabled": bool(row["enabled"]),
                    "configured": bool(row["configured"]),
                    "configuration": configuration,
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return results

    def delete(self, name: str) -> bool:
        with connection_scope(self.db_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM yoma_integrations
                WHERE name = ?
                """,
                (name,),
            )
            connection.commit()
            return cursor.rowcount > 0
