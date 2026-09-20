from datetime import datetime

from yoma.office.models.attendance import AttendanceEvent
from yoma.office.services.workforce import WorkforceService


def make_events(
    employee_id: str,
    check_in_hour: int = 9,
    check_out_hour: int = 17,
) -> list[AttendanceEvent]:
    return [
        AttendanceEvent(
            employee_id=employee_id,
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, check_in_hour, 0),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id=employee_id,
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, check_out_hour, 0),
            source="biometric",
        ),
    ]


def test_organization_provides_operational_signals():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.9,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002", 9, 17),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    assert "operational_signals" in result
    assert isinstance(result["operational_signals"], list)
    assert len(result["operational_signals"]) >= 1


def test_operational_signals_identify_high_workload():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.9,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002", 9, 17),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    signals = result["operational_signals"]

    assert any(
        signal["type"] == "high_workload"
        and signal["employee_id"] == "EMP001"
        for signal in signals
    )


def test_operational_signals_identify_department_pressure():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.9,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002", 8, 19),
            "deadline_pressure": 0.8,
            "meeting_load": 0.8,
            "consecutive_work_days": 6,
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    signals = result["operational_signals"]

    assert any(
        signal["type"] == "department_workload_pressure"
        and signal["department"] == "Engineering"
        for signal in signals
    )


def test_operational_signals_are_deterministic():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002"),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.9,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    signals = result["operational_signals"]

    assert signals == sorted(
        signals,
        key=lambda signal: (
            signal["type"],
            signal.get("department", ""),
            signal.get("employee_id", ""),
        ),
    )


def test_operational_signals_contain_evidence():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.9,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    signals = result["operational_signals"]

    assert signals

    for signal in signals:
        assert "type" in signal
        assert "severity" in signal
        assert "evidence" in signal
        assert isinstance(signal["evidence"], dict)


def test_operational_signals_do_not_make_employment_decisions():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.9,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    signals = result["operational_signals"]

    forbidden_types = {
        "termination",
        "disciplinary_action",
        "salary_action",
        "promotion",
        "demotion",
    }

    assert all(
        signal["type"] not in forbidden_types
        for signal in signals
    )