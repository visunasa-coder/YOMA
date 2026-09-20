from __future__ import annotations

from datetime import datetime
from ..models.attendance import AttendanceEvent
from ..models.workforce import WorkloadSignal, Recommendation
from .work_session import WorkSessionEngine
from ..intelligence.workforce import WorkIntelligenceEngine


class WorkforceService:
    """
    End-to-end workforce analysis pipeline.

    Attendance data is converted into work sessions and then
    into bounded workload recommendations.

    Recommendations always require human review.

    The service supports:
    - individual employee analysis
    - organization-level workforce aggregation
    - organization-level workforce risk identification
    - organization-level operational signals
    - organization-level recommendations
    - organization-level prioritization
    """

    HIGH_WORKLOAD_THRESHOLD = 0.70
    HIGH_RISK_DEPARTMENT_THRESHOLD = 0.70
    MEDIUM_RISK_DEPARTMENT_THRESHOLD = 0.40

    def __init__(self) -> None:
        self.session_engine = WorkSessionEngine()
        self.intelligence_engine = WorkIntelligenceEngine()

    def analyze_employee(
        self,
        employee_id: str,
        events: list[AttendanceEvent],
        *,
        deadline_pressure: float = 0.0,
        meeting_load: float = 0.0,
        consecutive_work_days: int = 1,
    ) -> dict:

        employee_events = [
            event
            for event in events
            if event.employee_id == employee_id
        ]

        sessions = self.session_engine.build_sessions(
            employee_events
        )

        total_hours = sum(
            self.session_engine.duration_hours(session)
            for session in sessions
        )

        overtime_hours = sum(
            self.session_engine.overtime_hours(session)
            for session in sessions
        )

        workload_score = self._workload_score(
            total_hours=total_hours,
            overtime_hours=overtime_hours,
            deadline_pressure=deadline_pressure,
            meeting_load=meeting_load,
        )

        signal = WorkloadSignal(
            employee_id=employee_id,
            workload_score=workload_score,
            overtime_hours=round(overtime_hours, 2),
            consecutive_work_days=consecutive_work_days,
            deadline_pressure=deadline_pressure,
            meeting_load=meeting_load,
        )

        recommendations = self.intelligence_engine.analyze(signal)

        return {
            "employee_id": employee_id,
            "sessions": sessions,
            "total_work_hours": round(total_hours, 2),
            "overtime_hours": round(overtime_hours, 2),
            "workload_score": workload_score,
            "recommendations": recommendations,
        }

    def analyze_organization(
        self,
        employees: list[dict],
    ) -> dict:
        """
        Analyze multiple employees and aggregate workforce metrics.

        Each employee is analyzed independently using analyze_employee().
        Attendance events are filtered by employee_id so that one
        employee's events cannot leak into another employee's result.

        Organization-level risk indicators, signals, recommendations,
        and priorities are operational only. They do not represent
        employment, disciplinary, salary, termination, promotion,
        or demotion decisions.
        """
        if not isinstance(employees, list):
            raise TypeError("Employees must be a list")

        employee_results: dict[str, dict] = {}
        employees_by_department: dict[str, int] = {}

        for employee in employees:
            if not isinstance(employee, dict):
                raise TypeError(
                    "Each employee must be a dictionary"
                )

            employee_id = employee.get("employee_id")

            if not isinstance(employee_id, str) or not employee_id.strip():
                raise ValueError(
                    "Each employee requires a valid employee_id"
                )

            events = employee.get("events")

            if not isinstance(events, list):
                raise TypeError(
                    f"Events for employee {employee_id} must be a list"
                )

            department = employee.get("department")

            if department is None:
                department = "Unassigned"

            if not isinstance(department, str):
                raise TypeError(
                    f"Department for employee {employee_id} must be a string"
                )

            department = department.strip() or "Unassigned"

            result = self.analyze_employee(
                employee_id,
                events,
                deadline_pressure=self._numeric_value(
                    employee.get("deadline_pressure", 0.0),
                    "deadline_pressure",
                ),
                meeting_load=self._numeric_value(
                    employee.get("meeting_load", 0.0),
                    "meeting_load",
                ),
                consecutive_work_days=self._integer_value(
                    employee.get("consecutive_work_days", 1),
                    "consecutive_work_days",
                ),
            )

            result["department"] = department

            employee_results[employee_id] = result

            employees_by_department[department] = (
                employees_by_department.get(department, 0) + 1
            )

        departments: dict[str, dict] = {}

        for department in sorted(employees_by_department):
            department_employee_ids = sorted(
                employee_id
                for employee_id, result in employee_results.items()
                if result["department"] == department
            )

            department_results = [
                employee_results[employee_id]
                for employee_id in department_employee_ids
            ]

            workload_scores = [
                float(result["workload_score"])
                for result in department_results
            ]

            high_workload_count = sum(
                score >= self.HIGH_WORKLOAD_THRESHOLD
                for score in workload_scores
            )

            average_workload_score = (
                sum(workload_scores) / len(workload_scores)
                if workload_scores
                else 0.0
            )

            average_workload_score = round(
                average_workload_score,
                2,
            )

            departments[department] = {
                "employee_count": len(department_results),
                "average_workload_score": average_workload_score,
                "high_workload_count": high_workload_count,
                "risk_level": self._risk_level(
                    average_workload_score
                ),
            }

        risk_employees = sorted(
            employee_id
            for employee_id, result in employee_results.items()
            if float(result["workload_score"])
            >= self.HIGH_WORKLOAD_THRESHOLD
        )

        risk_departments = sorted(
            department
            for department, metrics in departments.items()
            if metrics["risk_level"] == "high"
        )

        operational_signals = self._build_operational_signals(
            employee_results=employee_results,
            departments=departments,
        )

        organization_recommendations = (
            self._build_organization_recommendations(
                employee_results=employee_results,
                departments=departments,
            )
        )

        priority_items = self._build_priority_items(
            employee_results=employee_results,
            departments=departments,
        )

        return {
            "total_employees": len(employee_results),
            "departments": departments,
            "employees_by_department": dict(
                sorted(employees_by_department.items())
            ),
            "employee_results": {
                employee_id: employee_results[employee_id]
                for employee_id in sorted(employee_results)
            },
            "risk_employees": risk_employees,
            "risk_departments": risk_departments,
            "operational_signals": operational_signals,
            "organization_recommendations": organization_recommendations,
            "priority_items": priority_items,
        }

    def _build_operational_signals(
        self,
        *,
        employee_results: dict[str, dict],
        departments: dict[str, dict],
    ) -> list[dict]:
        """
        Build deterministic operational signals from workforce metrics.

        Signals describe workload conditions only. They do not prescribe
        employment actions.
        """
        signals: list[dict] = []

        for employee_id in sorted(employee_results):
            result = employee_results[employee_id]
            workload_score = float(result["workload_score"])

            if workload_score >= self.HIGH_WORKLOAD_THRESHOLD:
                signals.append(
                    {
                        "type": "high_workload",
                        "severity": "high",
                        "employee_id": employee_id,
                        "evidence": {
                            "workload_score": workload_score,
                            "total_work_hours": result[
                                "total_work_hours"
                            ],
                            "overtime_hours": result[
                                "overtime_hours"
                            ],
                        },
                    }
                )

        for department in sorted(departments):
            metrics = departments[department]

            if metrics["risk_level"] == "high":
                signals.append(
                    {
                        "type": "department_workload_pressure",
                        "severity": "high",
                        "department": department,
                        "evidence": {
                            "employee_count": metrics[
                                "employee_count"
                            ],
                            "average_workload_score": metrics[
                                "average_workload_score"
                            ],
                            "high_workload_count": metrics[
                                "high_workload_count"
                            ],
                        },
                    }
                )

        return sorted(
            signals,
            key=lambda signal: (
                signal["type"],
                signal.get("department", ""),
                signal.get("employee_id", ""),
            ),
        )

    def _build_organization_recommendations(
        self,
        *,
        employee_results: dict[str, dict],
        departments: dict[str, dict],
    ) -> list[dict]:
        """
        Build organization-level recommendations from operational
        workload conditions.

        These recommendations are advisory and always require
        human review.
        """
        recommendations: list[dict] = []

        for department in sorted(departments):
            metrics = departments[department]

            if metrics["risk_level"] == "high":
                recommendations.append(
                    {
                        "type": "department_workload_review",
                        "department": department,
                        "reason": (
                            "Department workload pressure is high "
                            "and should be reviewed by an authorized "
                            "human decision-maker."
                        ),
                        "evidence": {
                            "employee_count": metrics[
                                "employee_count"
                            ],
                            "average_workload_score": metrics[
                                "average_workload_score"
                            ],
                            "high_workload_count": metrics[
                                "high_workload_count"
                            ],
                        },
                        "requires_human_approval": True,
                    }
                )

        for employee_id in sorted(employee_results):
            result = employee_results[employee_id]

            if float(result["workload_score"]) >= self.HIGH_WORKLOAD_THRESHOLD:
                recommendations.append(
                    {
                        "type": "employee_workload_review",
                        "employee_id": employee_id,
                        "reason": (
                            "Employee workload indicators are high "
                            "and should be reviewed by an authorized "
                            "human decision-maker."
                        ),
                        "evidence": {
                            "workload_score": result[
                                "workload_score"
                            ],
                            "total_work_hours": result[
                                "total_work_hours"
                            ],
                            "overtime_hours": result[
                                "overtime_hours"
                            ],
                        },
                        "requires_human_approval": True,
                    }
                )

        return sorted(
            recommendations,
            key=lambda recommendation: (
                recommendation["type"],
                recommendation.get("department", ""),
                recommendation.get("employee_id", ""),
            ),
        )

    def _build_priority_items(
        self,
        *,
        employee_results: dict[str, dict],
        departments: dict[str, dict],
    ) -> list[dict]:
        """
        Build deterministic organization-level priority items.

        Priority is an operational ordering mechanism only. It does
        not execute actions or make employment decisions.

        High-risk workload conditions receive high priority.
        Other recognized workload conditions receive medium priority.
        """
        priority_items: list[dict] = []

        for department in sorted(departments):
            metrics = departments[department]

            if metrics["risk_level"] == "high":
                priority_items.append(
                    {
                        "priority": "high",
                        "type": "department_workload_review",
                        "department": department,
                        "reason": (
                            "Department workload pressure is high "
                            "and should be reviewed first."
                        ),
                        "evidence": {
                            "employee_count": metrics[
                                "employee_count"
                            ],
                            "average_workload_score": metrics[
                                "average_workload_score"
                            ],
                            "high_workload_count": metrics[
                                "high_workload_count"
                            ],
                        },
                        "requires_human_approval": True,
                    }
                )

        for employee_id in sorted(employee_results):
            result = employee_results[employee_id]
            workload_score = float(result["workload_score"])

            if workload_score >= self.HIGH_WORKLOAD_THRESHOLD:
                priority_items.append(
                    {
                        "priority": "high",
                        "type": "employee_workload_review",
                        "employee_id": employee_id,
                        "department": result["department"],
                        "reason": (
                            "Employee workload indicators are high "
                            "and should be reviewed first."
                        ),
                        "evidence": {
                            "workload_score": workload_score,
                            "total_work_hours": result[
                                "total_work_hours"
                            ],
                            "overtime_hours": result[
                                "overtime_hours"
                            ],
                        },
                        "requires_human_approval": True,
                    }
                )

        return sorted(
            priority_items,
            key=lambda item: (
                item["priority"],
                item.get("department", ""),
                item.get("employee_id", ""),
                item["type"],
            ),
        )

    @classmethod
    def _risk_level(
        cls,
        average_workload_score: float,
    ) -> str:
        """
        Convert an aggregate workload score into an operational
        risk indicator.
        """
        if average_workload_score >= cls.HIGH_RISK_DEPARTMENT_THRESHOLD:
            return "high"

        if average_workload_score >= cls.MEDIUM_RISK_DEPARTMENT_THRESHOLD:
            return "medium"

        return "low"

    @staticmethod
    def _numeric_value(
        value: float,
        field_name: str,
    ) -> float:
        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be numeric"
            )

        if not isinstance(value, (int, float)):
            raise TypeError(
                f"{field_name} must be numeric"
            )

        return float(value)

    @staticmethod
    def _integer_value(
        value: int,
        field_name: str,
    ) -> int:
        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if not isinstance(value, int):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        return value

    @staticmethod
    def _workload_score(
        *,
        total_hours: float,
        overtime_hours: float,
        deadline_pressure: float,
        meeting_load: float,
    ) -> float:

        score = (
            min(total_hours / 8.0, 1.5) * 0.35
            + min(overtime_hours / 4.0, 1.0) * 0.25
            + min(max(deadline_pressure, 0.0), 1.0) * 0.20
            + min(max(meeting_load, 0.0), 1.0) * 0.20
        )

        return round(min(score, 1.0), 2)