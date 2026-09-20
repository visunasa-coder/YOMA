from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from yoma.office.operations import OperationalEvent, OperationalEventBus


class IntegrationEventBridge:
    """
    Converts external/adapter records into YOMA OperationalEvents.

    The bridge deliberately does not assume a particular vendor,
    protocol, database, or SaaS provider.
    """

    def __init__(self, bus: OperationalEventBus | None = None) -> None:
        self.bus = bus or OperationalEventBus()

    @staticmethod
    def _timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value

        if isinstance(value, str) and value.strip():
            text = value.strip()

            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            try:
                parsed = datetime.fromisoformat(text)

                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)

                return parsed
            except ValueError:
                pass

        return datetime.now(timezone.utc)

    def normalize(
        self,
        *,
        source: str,
        event_type: str,
        record: dict[str, Any],
        event_id: str | None = None,
        occurred_at: Any = None,
        organization_id: str | None = None,
        user_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        severity: str = "info",
    ) -> OperationalEvent:
        if not source or not source.strip():
            raise ValueError("source is required")

        if not event_type or not event_type.strip():
            raise ValueError("event_type is required")

        if not isinstance(record, dict):
            raise TypeError("record must be a dictionary")

        resolved_id = event_id or record.get("id")

        if not resolved_id:
            raise ValueError("event_id is required")

        return OperationalEvent(
            event_id=str(resolved_id),
            event_type=event_type.strip(),
            occurred_at=self._timestamp(
                occurred_at if occurred_at is not None
                else record.get("occurred_at")
            ),
            organization_id=organization_id,
            user_id=user_id,
            system_id=system_id,
            source=source.strip(),
            location_id=location_id,
            severity=severity,
            data=dict(record),
        )

    def ingest(
        self,
        *,
        source: str,
        event_type: str,
        record: dict[str, Any],
        **kwargs: Any,
    ) -> OperationalEvent:
        event = self.normalize(
            source=source,
            event_type=event_type,
            record=record,
            **kwargs,
        )

        self.bus.publish(event)
        return event

    def ingest_many(
        self,
        records: Iterable[dict[str, Any]],
        *,
        source: str,
        event_type: str,
        **kwargs: Any,
    ) -> list[OperationalEvent]:
        events = [
            self.normalize(
                source=source,
                event_type=event_type,
                record=record,
                **kwargs,
            )
            for record in records
        ]

        self.bus.publish_many(events)

        return events
