from datetime import datetime

from yoma.office.models.attendance import AttendanceEvent
from yoma.office.services.workforce import WorkforceService
from yoma.office.intelligence.workforce import WorkIntelligenceEngine
from yoma.office.models.workforce import WorkloadSignal


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


def test_workforce_intelligence_analyzes_multiple_employees():
    service = WorkforceService()

    result_one = service.analyze_employee(
        "EMP001",
        make_events("EMP001", 9, 18),
        deadline_pressure=0.7,
        meeting_load=0.5,
        consecutive_work_days=5,
    )

    result_two = service.analyze_employee(
        "EMP002",
        make_events("EMP002", 9, 17),
        deadline_pressure=0.2,
        meeting_load=0.2,
        consecutive_work_days=3,
    )

    assert result_one["employee_id"] == "EMP001"
    assert result_two["employee_id"] == "EMP002"


def test_workforce_intelligence_identifies_high_workload_employee():
    service = WorkforceService()

    result = service.analyze_employee(
        "EMP001",
        make_events("EMP001", 8, 20),
        deadline_pressure=0.9,
        meeting_load=0.9,
        consecutive_work_days=7,
    )

    assert result["workload_score"] > 0.5
    assert result["recommendations"]


def test_workforce_intelligence_identifies_normal_workload_employee():
    service = WorkforceService()

    result = service.analyze_employee(
        "EMP001",
        make_events("EMP001", 9, 17),
        deadline_pressure=0.1,
        meeting_load=0.1,
        consecutive_work_days=2,
    )

    assert 0.0 <= result["workload_score"] <= 1.0
    assert result["employee_id"] == "EMP001"


def test_workload_signal_can_be_analyzed_into_recommendations():
    signal = WorkloadSignal(
        employee_id="EMP001",
        workload_score=0.95,
        overtime_hours=5,
        consecutive_work_days=7,
        deadline_pressure=0.95,
        meeting_load=0.9,
    )

    recommendations = WorkIntelligenceEngine().analyze(signal)

    assert len(recommendations) >= 2

    recommendation_types = {
        recommendation.recommendation_type
        for recommendation in recommendations
    }

    assert "recovery_leave_review" in recommendation_types
    assert "workload_review" in recommendation_types


def test_workforce_analysis_does_not_cross_employee_boundaries():
    service = WorkforceService()

    events = (
        make_events("EMP001", 9, 18)
        + make_events("EMP002", 8, 20)
    )

    result = service.analyze_employee(
        "EMP001",
        events,
        deadline_pressure=0.8,
        meeting_load=0.8,
        consecutive_work_days=5,
    )

    assert result["employee_id"] == "EMP001"

    assert all(
        session.employee_id == "EMP001"
        for session in result["sessions"]
    )


def test_workforce_recommendations_require_human_approval():
    service = WorkforceService()

    result = service.analyze_employee(
        "EMP001",
        make_events("EMP001", 8, 20),
        deadline_pressure=0.95,
        meeting_load=0.95,
        consecutive_work_days=7,
    )

    assert result["recommendations"]

    assert all(
        recommendation.requires_human_approval
        for recommendation in result["recommendations"]
    )