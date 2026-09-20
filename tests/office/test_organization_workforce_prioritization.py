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


def test_organization_provides_prioritized_workforce_items():
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
            "events": make_events("EMP002"),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    assert "priority_items" in result
    assert isinstance(result["priority_items"], list)
    assert len(result["priority_items"]) >= 1


def test_high_workload_employee_gets_high_priority():
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
            "events": make_events("EMP002"),
            "deadline_pressure": 0.1,
            "meeting_load": 0.1,
            "consecutive_work_days": 2,
            "department": "Sales",
        },
    ]

    result = service.analyze_organization(employees)

    priority_items = result["priority_items"]

    employee_item = next(
        item
        for item in priority_items
        if item.get("employee_id") == "EMP001"
    )

    assert employee_item["priority"] == "high"


def test_high_risk_department_gets_high_priority():
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

    priority_items = result["priority_items"]

    department_item = next(
        item
        for item in priority_items
        if item.get("department") == "Engineering"
    )

    assert department_item["priority"] == "high"


def test_priority_items_have_evidence_and_reason():
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

    assert result["priority_items"]

    for item in result["priority_items"]:
        assert "priority" in item
        assert "reason" in item
        assert "evidence" in item
        assert isinstance(item["evidence"], dict)


def test_priority_items_are_deterministic():
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

    priority_items = result["priority_items"]

    assert priority_items == sorted(
        priority_items,
        key=lambda item: (
            item["priority"],
            item.get("department", ""),
            item.get("employee_id", ""),
        ),
    )


def test_prioritization_does_not_execute_actions():
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

    for item in result["priority_items"]:
        assert "action_executed" not in item
        assert item.get("requires_human_approval", True) is True