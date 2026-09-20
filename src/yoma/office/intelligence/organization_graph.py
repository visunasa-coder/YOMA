from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from yoma.office.models.organization import (
    Department,
    Employee,
    Location,
    Organization,
    Team,
)


@dataclass(frozen=True)
class OrganizationGraphNode:
    node_id: str
    node_type: str
    name: str


@dataclass(frozen=True)
class OrganizationGraphEdge:
    source_id: str
    relationship: str
    target_id: str


class OrganizationGraph:
    """
    Deterministic organization relationship graph.

    The graph is derived only from explicit organization-model IDs.
    No relationship is inferred from names, roles, or free-form strings.
    """

    def __init__(
        self,
        organizations: Optional[Iterable[Organization]] = None,
        locations: Optional[Iterable[Location]] = None,
        departments: Optional[Iterable[Department]] = None,
        teams: Optional[Iterable[Team]] = None,
        employees: Optional[Iterable[Employee]] = None,
    ) -> None:
        self.organizations = list(organizations or [])
        self.locations = list(locations or [])
        self.departments = list(departments or [])
        self.teams = list(teams or [])
        self.employees = list(employees or [])

        self._nodes: dict[str, OrganizationGraphNode] = {}
        self._edges: list[OrganizationGraphEdge] = []

        self._build()

    def _add_node(self, node_id: str, node_type: str, name: str) -> None:
        self._nodes[node_id] = OrganizationGraphNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
        )

    def _add_edge(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
    ) -> None:
        if source_id in self._nodes and target_id in self._nodes:
            edge = OrganizationGraphEdge(
                source_id=source_id,
                relationship=relationship,
                target_id=target_id,
            )
            if edge not in self._edges:
                self._edges.append(edge)

    def _build(self) -> None:
        for organization in self.organizations:
            self._add_node(
                organization.organization_id,
                "organization",
                organization.name,
            )

        for location in self.locations:
            self._add_node(
                location.location_id,
                "location",
                location.name,
            )

        for department in self.departments:
            self._add_node(
                department.department_id,
                "department",
                department.name,
            )

        for team in self.teams:
            self._add_node(
                team.team_id,
                "team",
                team.name,
            )

        for employee in self.employees:
            self._add_node(
                employee.employee_id,
                "employee",
                employee.name,
            )

        for location in self.locations:
            self._add_edge(
                location.location_id,
                "BELONGS_TO",
                location.organization_id,
            )

        for department in self.departments:
            self._add_edge(
                department.department_id,
                "BELONGS_TO",
                department.organization_id,
            )

            if department.location_id:
                self._add_edge(
                    department.department_id,
                    "LOCATED_AT",
                    department.location_id,
                )

            if department.manager_employee_id:
                self._add_edge(
                    department.department_id,
                    "MANAGED_BY",
                    department.manager_employee_id,
                )

        for team in self.teams:
            self._add_edge(
                team.team_id,
                "BELONGS_TO",
                team.organization_id,
            )

            if team.department_id:
                self._add_edge(
                    team.team_id,
                    "PART_OF",
                    team.department_id,
                )

            if team.manager_employee_id:
                self._add_edge(
                    team.team_id,
                    "MANAGED_BY",
                    team.manager_employee_id,
                )

        for employee in self.employees:
            if employee.organization_id:
                self._add_edge(
                    employee.employee_id,
                    "BELONGS_TO",
                    employee.organization_id,
                )

            if employee.department_id:
                self._add_edge(
                    employee.employee_id,
                    "MEMBER_OF",
                    employee.department_id,
                )

            if employee.team_id:
                self._add_edge(
                    employee.employee_id,
                    "MEMBER_OF",
                    employee.team_id,
                )

            if employee.location_id:
                self._add_edge(
                    employee.employee_id,
                    "LOCATED_AT",
                    employee.location_id,
                )

            if employee.manager_employee_id:
                self._add_edge(
                    employee.employee_id,
                    "REPORTS_TO",
                    employee.manager_employee_id,
                )

    def nodes(self) -> list[OrganizationGraphNode]:
        return list(self._nodes.values())

    def edges(self) -> list[OrganizationGraphEdge]:
        return list(self._edges)

    def node(self, node_id: str) -> Optional[OrganizationGraphNode]:
        return self._nodes.get(node_id)

    def relationships(
        self,
        node_id: Optional[str] = None,
        relationship: Optional[str] = None,
    ) -> list[OrganizationGraphEdge]:
        return [
            edge
            for edge in self._edges
            if (node_id is None or edge.source_id == node_id)
            and (
                relationship is None
                or edge.relationship == relationship
            )
        ]

    def children(
        self,
        node_id: str,
        relationship: Optional[str] = None,
    ) -> list[OrganizationGraphNode]:
        target_ids = {
            edge.target_id
            for edge in self._edges
            if edge.source_id == node_id
            and (
                relationship is None
                or edge.relationship == relationship
            )
        }

        return [
            self._nodes[target_id]
            for target_id in self._nodes
            if target_id in target_ids
        ]

    def members_of(self, node_id: str) -> list[OrganizationGraphNode]:
        """
        Return employees explicitly associated with a department or team.

        MEMBER_OF edges are stored from employee -> organization unit,
        so this query traverses those edges in reverse.
        """
        member_ids = {
            edge.source_id
            for edge in self._edges
            if edge.target_id == node_id
            and edge.relationship == "MEMBER_OF"
        }

        return [
            self._nodes[member_id]
            for member_id in self._nodes
            if member_id in member_ids
        ]

    def reports_to(self, employee_id: str) -> Optional[OrganizationGraphNode]:
        """
        Return the explicit manager of an employee.
        """
        matches = self.children(employee_id, "REPORTS_TO")
        return matches[0] if matches else None

    def manager_of(self, node_id: str) -> Optional[OrganizationGraphNode]:
        """
        Return the explicit manager of a department or team.
        """
        matches = self.children(node_id, "MANAGED_BY")
        return matches[0] if matches else None

    def department_of(self, employee_id: str) -> Optional[OrganizationGraphNode]:
        """
        Return the department explicitly associated with an employee.
        """
        matches = self.children(employee_id, "MEMBER_OF")

        for match in matches:
            if match.node_type == "department":
                return match

        return None

    def team_of(self, employee_id: str) -> Optional[OrganizationGraphNode]:
        """
        Return the team explicitly associated with an employee.
        """
        matches = self.children(employee_id, "MEMBER_OF")

        for match in matches:
            if match.node_type == "team":
                return match

        return None

    def location_of(self, employee_id: str) -> Optional[OrganizationGraphNode]:
        """
        Return the explicit location associated with an employee.
        """
        matches = self.children(employee_id, "LOCATED_AT")
        return matches[0] if matches else None

    def organization_of(self, node_id: str) -> Optional[OrganizationGraphNode]:
        """
        Return the organization explicitly associated with a node.
        """
        direct = self.children(node_id, "BELONGS_TO")

        for match in direct:
            if match.node_type == "organization":
                return match

        return None

    def organizational_path(
        self,
        employee_id: str,
    ) -> list[OrganizationGraphNode]:
        """
        Return the explicit employee -> team -> department ->
        organization path where those relationships exist.

        Missing intermediate relationships are not inferred.
        """
        employee = self.node(employee_id)

        if employee is None or employee.node_type != "employee":
            return []

        path = [employee]

        team = self.team_of(employee_id)
        if team is not None:
            path.append(team)

        department = self.department_of(employee_id)
        if department is not None:
            path.append(department)

        organization = self.organization_of(employee_id)
        if organization is None and department is not None:
            organization = self.organization_of(department.node_id)

        if organization is not None:
            path.append(organization)

        return path

    def snapshot(self) -> dict:
        return {
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "name": node.name,
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "source_id": edge.source_id,
                    "relationship": edge.relationship,
                    "target_id": edge.target_id,
                }
                for edge in self._edges
            ],
        }
