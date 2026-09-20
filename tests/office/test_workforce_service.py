from datetime import datetime

from yoma.office.models.attendance import AttendanceEvent
from yoma.office.services.workforce import WorkforceService


def test_workforce_pipeline_produces_workload_analysis():

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

    result = WorkforceService().analyze_employee(
        "EMP001",
        events,
        deadline_pressure=0.9,
        meeting_load=0.3,
        consecutive_work_days=6,
    )

    assert result["employee_id"] == "EMP001"
    assert result["total_work_hours"] == 10.0
    assert result["overtime_hours"] == 2.0
    assert 0.0 <= result["workload_score"] <= 1.0

    assert any(
        recommendation.recommendation_type == "workload_review"
        for recommendation in result["recommendations"]
    )


def test_workforce_pipeline_isolates_employee():

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
        AttendanceEvent(
            employee_id="EMP002",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 9, 0),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP002",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 17, 0),
            source="biometric",
        ),
    ]

    result = WorkforceService().analyze_employee(
        "EMP001",
        events,
    )

    assert result["employee_id"] == "EMP001"
    assert result["total_work_hours"] == 9.0
    assert all(
        session.employee_id == "EMP001"
        for session in result["sessions"]
    )


def test_recommendations_require_human_approval():

    events = [
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_in",
            timestamp=datetime(2026, 9, 2, 8, 0),
            source="biometric",
        ),
        AttendanceEvent(
            employee_id="EMP001",
            event_type="check_out",
            timestamp=datetime(2026, 9, 2, 19, 0),
            source="biometric",
        ),
    ]

    result = WorkforceService().analyze_employee(
        "EMP001",
        events,
        deadline_pressure=0.9,
        meeting_load=0.9,
        consecutive_work_days=7,
    )

    assert result["recommendations"]

    assert all(
        recommendation.requires_human_approval
        for recommendation in result["recommendations"]
    )
