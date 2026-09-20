from yoma.office.intelligence.workforce import WorkIntelligenceEngine
from yoma.office.models.workforce import WorkloadSignal


def test_work_intelligence_recommends_recovery_review():
    signal = WorkloadSignal(
        employee_id="EMP001",
        workload_score=0.9,
        overtime_hours=4,
        consecutive_work_days=6,
        deadline_pressure=0.4,
        meeting_load=0.3,
    )

    recommendations = WorkIntelligenceEngine().analyze(signal)

    assert any(
        r.recommendation_type == "recovery_leave_review"
        for r in recommendations
    )
