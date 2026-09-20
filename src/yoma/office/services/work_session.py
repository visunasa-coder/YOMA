from __future__ import annotations

from datetime import datetime
from ..models.attendance import AttendanceEvent
from ..models.workforce import WorkSession


class WorkSessionEngine:
    """
    Converts normalized attendance events into YOMA work sessions.

    The engine does not make employment decisions.
    It only calculates operational work-session data.
    """

    def build_sessions(
        self,
        events: list[AttendanceEvent],
    ) -> list[WorkSession]:

        if not events:
            return []

        ordered = sorted(
            events,
            key=lambda event: event.timestamp,
        )

        sessions: list[WorkSession] = []
        open_sessions: dict[str, datetime] = {}

        for event in ordered:

            employee_id = event.employee_id

            if event.event_type == "check_in":

                # Ignore duplicate check-ins while a session is open.
                if employee_id not in open_sessions:
                    open_sessions[employee_id] = event.timestamp

            elif event.event_type == "check_out":

                started_at = open_sessions.pop(
                    employee_id,
                    None,
                )

                if started_at is None:
                    continue

                if event.timestamp <= started_at:
                    continue

                sessions.append(
                    WorkSession(
                        employee_id=employee_id,
                        started_at=started_at,
                        ended_at=event.timestamp,
                        source=event.source,
                    )
                )

        # Preserve incomplete sessions so the caller can identify
        # employees currently working or missing a checkout.
        for employee_id, started_at in open_sessions.items():
            sessions.append(
                WorkSession(
                    employee_id=employee_id,
                    started_at=started_at,
                    ended_at=None,
                    source="attendance",
                )
            )

        return sorted(
            sessions,
            key=lambda session: session.started_at,
        )

    def duration_hours(
        self,
        session: WorkSession,
    ) -> float:

        if session.ended_at is None:
            return 0.0

        if session.ended_at <= session.started_at:
            return 0.0

        return round(
            (
                session.ended_at - session.started_at
            ).total_seconds() / 3600,
            2,
        )

    def overtime_hours(
        self,
        session: WorkSession,
        standard_hours: float = 8.0,
    ) -> float:

        duration = self.duration_hours(session)

        return round(
            max(0.0, duration - standard_hours),
            2,
        )
