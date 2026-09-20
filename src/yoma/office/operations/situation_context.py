from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yoma.office.intelligence.organization_graph import (
    OrganizationGraph,
    OrganizationGraphNode,
)
from yoma.office.operations.situation import OperationalSituation


@dataclass(frozen=True)
class OperationalSituationContext:
    """
    Explicit organizational context resolved for an operational
    situation.

    Context is derived only from OrganizationGraph relationships.
    No names, roles, free text, or inferred relationships are used.
    """

    situation: OperationalSituation
    employee_id: Optional[str] = None
    team: Optional[OrganizationGraphNode] = None
    department: Optional[OrganizationGraphNode] = None
    location: Optional[OrganizationGraphNode] = None
    organization: Optional[OrganizationGraphNode] = None

    @property
    def situation_id(self) -> str:
        return self.situation.situation_id


class OperationalSituationContextResolver:
    """
    Resolves explicit organizational context for an
    OperationalSituation.

    Employee context is resolved only when the situation has an
    explicit user_id that exists in the organization graph.

    Organization context for system-level situations is resolved
    only from an explicit organization_id.
    """

    def __init__(self, graph: OrganizationGraph) -> None:
        if not isinstance(graph, OrganizationGraph):
            raise TypeError("graph must be an OrganizationGraph")

        self._graph = graph

    def resolve(
        self,
        situation: OperationalSituation,
    ) -> OperationalSituationContext:
        if not isinstance(situation, OperationalSituation):
            raise TypeError(
                "situation must be an OperationalSituation"
            )

        employee_id = situation.user_id

        team = None
        department = None
        location = None
        organization = None

        if employee_id is not None:
            employee_node = self._graph.node(employee_id)

            if (
                employee_node is not None
                and employee_node.node_type == "employee"
            ):
                team = self._graph.team_of(employee_id)
                department = self._graph.department_of(employee_id)
                location = self._graph.location_of(employee_id)
                organization = self._graph.organization_of(
                    employee_id
                )

        elif situation.organization_id is not None:
            candidate = self._graph.node(
                situation.organization_id
            )

            if (
                candidate is not None
                and candidate.node_type == "organization"
            ):
                organization = candidate

        return OperationalSituationContext(
            situation=situation,
            employee_id=employee_id,
            team=team,
            department=department,
            location=location,
            organization=organization,
        )
