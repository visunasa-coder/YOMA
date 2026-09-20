from __future__ import annotations

from ..models.workforce import Recommendation, WorkloadSignal


class WorkIntelligenceEngine:
    """
    Analyzes normalized workplace signals.

    This engine recommends actions; it does not autonomously
    approve leave, discipline employees, or make employment decisions.
    """

    def analyze(self, signal: WorkloadSignal) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        if (
            signal.overtime_hours >= 3
            and signal.consecutive_work_days >= 5
        ):
            recommendations.append(
                Recommendation(
                    employee_id=signal.employee_id,
                    recommendation_type="recovery_leave_review",
                    reason=(
                        "Sustained workload and overtime indicate that "
                        "HR may consider a recovery period."
                    ),
                )
            )

        if signal.deadline_pressure >= 0.8:
            recommendations.append(
                Recommendation(
                    employee_id=signal.employee_id,
                    recommendation_type="workload_review",
                    reason=(
                        "High deadline pressure suggests reviewing "
                        "task allocation or schedule."
                    ),
                )
            )

        if signal.meeting_load >= 0.8:
            recommendations.append(
                Recommendation(
                    employee_id=signal.employee_id,
                    recommendation_type="focus_time_review",
                    reason=(
                        "High meeting load suggests protecting "
                        "dedicated focus time."
                    ),
                )
            )

        return recommendations
