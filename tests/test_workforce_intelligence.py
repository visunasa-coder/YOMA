from yoma.office.intelligence.workforce import WorkIntelligenceEngine
from yoma.office.models.workforce import WorkloadSignal


def test_workload_signal_with_overtime_generates_recovery_review():
    signal = WorkloadSignal(
        employee_id="EMP-001",
        workload_score=0.9,
        overtime_hours=3,
        consecutive_work_days=5,
        deadline_pressure=0.0,
        meeting_load=0.0,
    )

    recommendations = WorkIntelligenceEngine().analyze(signal)

    assert len(recommendations) == 1
    assert recommendations[0].recommendation_type == "recovery_leave_review"
    assert recommendations[0].requires_human_approval is True


def test_high_deadline_pressure_generates_workload_review():
    signal = WorkloadSignal(
        employee_id="EMP-002",
        workload_score=0.7,
        overtime_hours=0,
        consecutive_work_days=2,
        deadline_pressure=0.8,
        meeting_load=0.0,
    )

    recommendations = WorkIntelligenceEngine().analyze(signal)

    assert len(recommendations) == 1
    assert recommendations[0].recommendation_type == "workload_review"


def test_high_meeting_load_generates_focus_time_review():
    signal = WorkloadSignal(
        employee_id="EMP-003",
        workload_score=0.6,
        overtime_hours=0,
        consecutive_work_days=2,
        deadline_pressure=0.0,
        meeting_load=0.8,
    )

    recommendations = WorkIntelligenceEngine().analyze(signal)

    assert len(recommendations) == 1
    assert recommendations[0].recommendation_type == "focus_time_review"


def test_normal_workload_generates_no_recommendations():
    signal = WorkloadSignal(
        employee_id="EMP-004",
        workload_score=0.3,
        overtime_hours=1,
        consecutive_work_days=2,
        deadline_pressure=0.2,
        meeting_load=0.2,
    )

    recommendations = WorkIntelligenceEngine().analyze(signal)

    assert recommendations == []
