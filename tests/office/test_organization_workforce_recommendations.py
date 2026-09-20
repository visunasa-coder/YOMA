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


def test_organization_provides_recommendations():
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

    assert "organization_recommendations" in result
    assert isinstance(
        result["organization_recommendations"],
        list,
    )


def test_organization_recommends_review_for_high_workload_department():
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

    recommendations = result["organization_recommendations"]

    assert any(
        recommendation["type"] == "department_workload_review"
        and recommendation["department"] == "Engineering"
        for recommendation in recommendations
    )


def test_organization_recommendations_include_evidence():
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

    recommendations = result["organization_recommendations"]

    assert recommendations

    for recommendation in recommendations:
        assert "type" in recommendation
        assert "reason" in recommendation
        assert "evidence" in recommendation
        assert isinstance(
            recommendation["evidence"],
            dict,
        )


def test_organization_recommendations_are_deterministic():
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

    recommendations = result["organization_recommendations"]

    assert recommendations == sorted(
        recommendations,
        key=lambda recommendation: (
            recommendation["type"],
            recommendation.get("department", ""),
            recommendation.get("employee_id", ""),
        ),
    )


def test_organization_recommendations_require_human_review():
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

    recommendations = result["organization_recommendations"]

    assert recommendations

    for recommendation in recommendations:
        assert recommendation["requires_human_approval"] is True


def test_organization_recommendations_do_not_make_employment_decisions():
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

    recommendations = result["organization_recommendations"]

    forbidden_types = {
        "termination",
        "disciplinary_action",
        "salary_action",
        "promotion",
        "demotion",
        "automatic_leave",
    }

    assert all(
        recommendation["type"] not in forbidden_types
        for recommendation in recommendations
    )