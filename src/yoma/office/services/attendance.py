from __future__ import annotations

from datetime import datetime
from ..models.attendance import AttendanceEvent, AttendanceRecord


class AttendanceService:
    """
    Converts events from any attendance adapter into
    YOMA's normalized attendance representation.
    """

    VALID_EVENT_TYPES = {"check_in", "check_out"}

    def normalize_event(self, event: dict) -> AttendanceEvent:
        employee_id = str(event.get("employee_id", "")).strip()
        event_type = str(event.get("event_type", "")).strip().lower()
        timestamp = event.get("timestamp")
        source = str(event.get("source", "")).strip()

        if not employee_id:
            raise ValueError("employee_id is required")

        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(f"Unsupported attendance event: {event_type}")

        if not timestamp:
            raise ValueError("timestamp is required")

        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        if not isinstance(timestamp, datetime):
            raise ValueError("timestamp must be a datetime or ISO timestamp")

        if not source:
            raise ValueError("source is required")

        return AttendanceEvent(
            employee_id=employee_id,
            event_type=event_type,
            timestamp=timestamp,
            source=source,
            device_id=event.get("device_id"),
            confidence=event.get("confidence"),
            metadata=event.get("metadata"),
        )

    def build_record(
        self,
        events: list[AttendanceEvent],
    ) -> AttendanceRecord:
        if not events:
            raise ValueError("At least one attendance event is required")

        ordered = sorted(events, key=lambda event: event.timestamp)

        first_in = next(
            (event.timestamp for event in ordered if event.event_type == "check_in"),
            None,
        )

        last_out = next(
            (
                event.timestamp
                for event in reversed(ordered)
                if event.event_type == "check_out"
            ),
            None,
        )

        total_work_hours = 0.0

        if first_in and last_out and last_out > first_in:
            total_work_hours = (
                last_out - first_in
            ).total_seconds() / 3600

        return AttendanceRecord(
            employee_id=ordered[0].employee_id,
            first_in=first_in,
            last_out=last_out,
            total_work_hours=round(total_work_hours, 2),
            source=ordered[0].source,
        )
