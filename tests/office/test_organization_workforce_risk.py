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


def test_organization_workforce_identifies_high_risk_department():
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
        {
            "employee_id": "EMP003",
            "events": make_events("EMP003", 9, 17),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    assert "risk_departments" in result
    assert "Engineering" in result["risk_departments"]


def test_organization_workforce_identifies_high_risk_employees():
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

    assert "risk_employees" in result
    assert "EMP001" in result["risk_employees"]
    assert "EMP002" not in result["risk_employees"]


def test_organization_workforce_risk_is_based_on_department_metrics():
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
            "deadline_pressure": 0.0,
            "meeting_load": 0.0,
            "consecutive_work_days": 1,
            "department": "Engineering",
        },
    ]

    result = service.analyze_organization(employees)

    engineering = result["departments"]["Engineering"]

    assert engineering["employee_count"] == 2
    assert "risk_level" in engineering
    assert engineering["risk_level"] in {
        "low",
        "medium",
        "high",
    }


def test_organization_workforce_risk_is_deterministic():
    service = WorkforceService()

    employees = [
        {
            "employee_id": "EMP002",
            "events": make_events("EMP002", 9, 17),
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

    assert result["risk_departments"] == sorted(
        result["risk_departments"]
    )

    assert result["risk_employees"] == sorted(
        result["risk_employees"]
    )


def test_organization_workforce_risk_does_not_make_employment_decisions():
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

    assert "termination" not in result
    assert "disciplinary_action" not in result
    assert "salary_action" not in result


def test_organization_workforce_risk_preserves_human_review_boundary():
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

    for recommendation in result["employee_results"]["EMP001"][
        "recommendations"
    ]:
        assert recommendation.requires_human_approval is True