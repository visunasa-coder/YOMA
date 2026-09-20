from datetime import datetime

from yoma.office.models.attendance import AttendanceEvent
from yoma.office.services.work_session import WorkSessionEngine


def test_build_completed_work_session():

    events = [
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 30),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 17, 30),
            source="biometric",
        ),
    ]

    sessions = WorkSessionEngine().build_sessions(events)

    assert len(sessions) == 1
    assert sessions[0].employee_id == "EMP001"
    assert sessions[0].ended_at is not None


def test_duration_hours():

    events = [
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 30),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 17, 30),
            source="biometric",
        ),
    ]

    engine = WorkSessionEngine()
    session = engine.build_sessions(events)[0]

    assert engine.duration_hours(session) == 9.0


def test_overtime_is_calculated():

    events = [
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 30),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 18, 30),
            source="biometric",
        ),
    ]

    engine = WorkSessionEngine()
    session = engine.build_sessions(events)[0]

    assert engine.overtime_hours(session) == 2.0


def test_incomplete_session_is_preserved():

    events = [
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 30),
            source="biometric",
        ),
    ]

    sessions = WorkSessionEngine().build_sessions(events)

    assert len(sessions) == 1
    assert sessions[0].ended_at is None


def test_duplicate_check_in_does_not_create_duplicate_session():

    events = [
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 30),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 31),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 17, 30),
            source="biometric",
        ),
    ]

    sessions = WorkSessionEngine().build_sessions(events)

    assert len(sessions) == 1
    assert sessions[0].started_at == datetime(2026, 9, 2, 8, 30)
