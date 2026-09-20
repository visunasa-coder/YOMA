from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from yoma.audit import record as db_record


class PersistentAuditLog:
    """
    Persistent audit adapter for YOMA's existing audit_events table.

    This class deliberately uses the existing audit infrastructure
    instead of creating a second audit database.
    """

    def __init__(self, connection) -> None:
        self.connection = connection

    @staticmethod
    def _sanitize_metadata(
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        safe = dict(metadata or {})

        for key in list(safe):
            lowered = key.lower()

            if any(
                secret in lowered
                for secret in (
                    "token",
                    "secret",
                    "password",
                    "credential",
                    "authorization",
                )
            ):
                safe.pop(key)

        return safe

    def record(
        self,
        *,
        event_type: str,
        actor: str | None,
        request_id: str,
        action_type: str,
        status: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        details = {
            "request_id": request_id,
            "action_type": action_type,
            "status": status,
        }

        if reason is not None:
            details["reason"] = reason

        details.update(
            self._sanitize_metadata(metadata)
        )

        db_record(
            self.connection,
            event_type,
            actor,
            details,
        )
