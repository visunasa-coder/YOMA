from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yoma.office.intelligence.organization_graph import (
    OrganizationGraph,
    OrganizationGraphNode,
)


@dataclass(frozen=True)
class WorkforceOrganizationContext:
    employee_id: str
    team: Optional[OrganizationGraphNode] = None
    department: Optional[OrganizationGraphNode] = None
    location: Optional[OrganizationGraphNode] = None
    organization: Optional[OrganizationGraphNode] = None


class WorkforceOrganizationContextResolver:
    """
    Resolves explicit organizational context for workforce analysis.

    Resolution is based only on relationships already represented in
    OrganizationGraph. No names, roles, free text, or inferred
    relationships are used.
    """

    def __init__(self, graph: OrganizationGraph) -> None:
        self._graph = graph

    def resolve(
        self,
        employee_id: str,
    ) -> WorkforceOrganizationContext:
        if not isinstance(employee_id, str) or not employee_id.strip():
            raise ValueError("employee_id must be a non-empty string")

        return WorkforceOrganizationContext(
            employee_id=employee_id,
            team=self._graph.team_of(employee_id),
            department=self._graph.department_of(employee_id),
            location=self._graph.location_of(employee_id),
            organization=self._graph.organization_of(employee_id),
        )
