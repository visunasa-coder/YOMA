from datetime import datetime

import pytest

from yoma.office.services.attendance import AttendanceService


def test_normalize_check_in_event():
    service = AttendanceService()

    event = service.normalize_event(
        {
            "employee_id": "EMP001",
            "event_type": "check_in",
            "timestamp": "2026-09-02T08:30:00",
            "source": "biometric_zkteco",
            "device_id": "BIO-01",
        }
    )

    assert event.employee_id == "EMP001"
    assert event.event_type == "check_in"
    assert event.source == "biometric_zkteco"
    assert event.device_id == "BIO-01"


def test_normalize_rejects_unknown_event_type():
    service = AttendanceService()

    with pytest.raises(ValueError):
        service.normalize_event(
            {
                "employee_id": "EMP001",
                "event_type": "something_else",
                "timestamp": "2026-09-02T08:30:00",
                "source": "biometric",
            }
        )


def test_build_attendance_record():
    service = AttendanceService()

    check_in = service.normalize_event(
        {
            "employee_id": "EMP001",
            "event_type": "check_in",
            "timestamp": "2026-09-02T08:30:00",
            "source": "biometric",
        }
    )

    check_out = service.normalize_event(
        {
            "employee_id": "EMP001",
            "event_type": "check_out",
            "timestamp": "2026-09-02T17:30:00",
            "source": "biometric",
        }
    )

    record = service.build_record([check_out, check_in])

    assert record.employee_id == "EMP001"
    assert record.total_work_hours == 9.0
