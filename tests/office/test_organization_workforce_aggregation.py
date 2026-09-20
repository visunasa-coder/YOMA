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


def test_workforce_service_can_analyze_organization():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.8,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002", 9, 17),
            "deadline_pressure": 0.2,
            "meeting_load": 0.2,
            "consecutive_work_days": 3,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP003",
            "events": make_events("EMP003", 9, 18),
            "deadline_pressure": 0.6,
            "meeting_load": 0.5,
            "consecutive_work_days": 5,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    assert result["total_employees"] == 3
    assert list(result["departments"]) == [
        "Engineering",
        "Sales",
    ]


def test_organization_workforce_analysis_aggregates_departments():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20),
            "deadline_pressure": 0.9,
            "meeting_load": 0.8,
            "consecutive_work_days": 7,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002", 9, 17),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Engineering",
        },
        {
            "employee_id": "EMP003",
            "events": make_events("EMP003", 9, 17),
            "deadline_pressure": 0.2,
            "meeting_load": 0.2,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    assert result["employees_by_department"] == {
        "Engineering": 2,
        "Sales": 1,
    }


def test_organization_workforce_analysis_provides_department_workload():
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
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    engineering = result["departments"]["Engineering"]

    assert engineering["employee_count"] == 2
    assert 0.0 <= engineering["average_workload_score"] <= 1.0
    assert engineering["high_workload_count"] >= 1


def test_organization_workforce_analysis_is_deterministic():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002"),
            "deadline_pressure": 0.2,
            "meeting_load": 0.2,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001"),
            "deadline_pressure": 0.2,
            "meeting_load": 0.2,
            "consecutive_work_days": 2,
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    assert list(result["departments"]) == [
        "Engineering",
        "Sales",
    ]


def test_organization_workforce_analysis_preserves_employee_boundaries():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP001",
            "events": make_events("EMP001", 8, 20)
            + make_events("EMP002", 9, 17),
            "deadline_pressure": 0.8,
            "meeting_load": 0.8,
            "consecutive_work_days": 6,
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

    assert result["employee_results"]["EMP001"]["employee_id"] == "EMP001"
    assert result["employee_results"]["EMP002"]["employee_id"] == "EMP002"

    assert all(
        session.employee_id == "EMP001"
        for session in result["employee_results"]["EMP001"]["sessions"]
    )

    assert all(
        session.employee_id == "EMP002"
        for session in result["employee_results"]["EMP002"]["sessions"]
    )


def test_organization_workforce_analysis_rejects_invalid_input():
    service = WorkforceService()

    invalid_inputs = [
        None,
        {},
        "employees",
    ]

    for value in invalid_inputs:
        try:
            service.analyze_organization(value)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(
                "Invalid organization input was accepted"
            )