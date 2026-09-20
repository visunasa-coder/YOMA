from __future__ import annotations

from typing import Optional

from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.workforce_organization import (
    WorkforceOrganizationContext,
    WorkforceOrganizationContextResolver,
)
from yoma.office.models.attendance import AttendanceEvent
from yoma.office.services.workforce import WorkforceService


class OrganizationAwareWorkforceService:
    """
    Combines existing workforce analysis with explicit organization
    context from OrganizationGraph.

    The underlying WorkforceService remains unchanged.
    Organizational relationships are resolved only from explicit
    graph relationships.
    """

    def __init__(
        self,
        graph: OrganizationGraph,
        workforce_service: Optional[WorkforceService] = None,
    ) -> None:
        self._resolver = WorkforceOrganizationContextResolver(graph)
        self._workforce_service = workforce_service or WorkforceService()

    def analyze_employee(
        self,
        employee_id: str,
        events: list[AttendanceEvent],
        *,
        deadline_pressure: float = 0.0,
        meeting_load: float = 0.0,
        consecutive_work_days: int = 1,
    ) -> dict:
        analysis = self._workforce_service.analyze_employee(
            employee_id,
            events,
            deadline_pressure=deadline_pressure,
            meeting_load=meeting_load,
            consecutive_work_days=consecutive_work_days,
        )

        context = self._resolver.resolve(employee_id)

        return {
            "employee_id": employee_id,
            "workforce_analysis": analysis,
            "organization_context": context,
        }
