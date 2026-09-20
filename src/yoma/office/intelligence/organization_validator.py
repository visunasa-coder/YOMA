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
class OrganizationValidationIssue:
    issue_type: str
    source_id: str
    message: str
    target_id: Optional[str] = None


class OrganizationGraphValidator:
    """
    Validates explicit organization-model relationships.

    This validator reports structural inconsistencies only.
    It does not infer relationships, mutate models, or make
    employment, disciplinary, financial, or security decisions.
    """

    def __init__(
        self,
        *,
        organizations: Iterable[Organization] = (),
        locations: Iterable[Location] = (),
        departments: Iterable[Department] = (),
        teams: Iterable[Team] = (),
        employees: Iterable[Employee] = (),
    ) -> None:
        self.organizations = list(organizations)
        self.locations = list(locations)
        self.departments = list(departments)
        self.teams = list(teams)
        self.employees = list(employees)

    def validate(self) -> list[OrganizationValidationIssue]:
        issues: list[OrganizationValidationIssue] = []

        organizations = {
            item.organization_id: item
            for item in self.organizations
        }
        locations = {
            item.location_id: item
            for item in self.locations
        }
        departments = {
            item.department_id: item
            for item in self.departments
        }
        teams = {
            item.team_id: item
            for item in self.teams
        }
        employees = {
            item.employee_id: item
            for item in self.employees
        }

        issues.extend(
            self._duplicate_id_issues(
                "organization",
                [item.organization_id for item in self.organizations],
            )
        )
        issues.extend(
            self._duplicate_id_issues(
                "location",
                [item.location_id for item in self.locations],
            )
        )
        issues.extend(
            self._duplicate_id_issues(
                "department",
                [item.department_id for item in self.departments],
            )
        )
        issues.extend(
            self._duplicate_id_issues(
                "team",
                [item.team_id for item in self.teams],
            )
        )
        issues.extend(
            self._duplicate_id_issues(
                "employee",
                [item.employee_id for item in self.employees],
            )
        )

        for location in self.locations:
            if location.organization_id not in organizations:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        location.location_id,
                        "Location references a missing organization.",
                        location.organization_id,
                    )
                )

        for department in self.departments:
            if department.organization_id not in organizations:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        department.department_id,
                        "Department references a missing organization.",
                        department.organization_id,
                    )
                )

            if (
                department.location_id
                and department.location_id not in locations
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        department.department_id,
                        "Department references a missing location.",
                        department.location_id,
                    )
                )

            if (
                department.manager_employee_id
                and department.manager_employee_id not in employees
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        department.department_id,
                        "Department references a missing manager.",
                        department.manager_employee_id,
                    )
                )

            if (
                department.location_id in locations
                and locations[department.location_id].organization_id
                != department.organization_id
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "organization_mismatch",
                        department.department_id,
                        "Department and location belong to different organizations.",
                        department.location_id,
                    )
                )

        for team in self.teams:
            if team.organization_id not in organizations:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        team.team_id,
                        "Team references a missing organization.",
                        team.organization_id,
                    )
                )

            if team.department_id and team.department_id not in departments:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        team.team_id,
                        "Team references a missing department.",
                        team.department_id,
                    )
                )

            if (
                team.manager_employee_id
                and team.manager_employee_id not in employees
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        team.team_id,
                        "Team references a missing manager.",
                        team.manager_employee_id,
                    )
                )

            if (
                team.department_id in departments
                and departments[team.department_id].organization_id
                != team.organization_id
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "organization_mismatch",
                        team.team_id,
                        "Team and department belong to different organizations.",
                        team.department_id,
                    )
                )

        for employee in self.employees:
            if (
                employee.organization_id
                and employee.organization_id not in organizations
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        employee.employee_id,
                        "Employee references a missing organization.",
                        employee.organization_id,
                    )
                )

            if employee.department_id and employee.department_id not in departments:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        employee.employee_id,
                        "Employee references a missing department.",
                        employee.department_id,
                    )
                )

            if employee.team_id and employee.team_id not in teams:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        employee.employee_id,
                        "Employee references a missing team.",
                        employee.team_id,
                    )
                )

            if employee.location_id and employee.location_id not in locations:
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        employee.employee_id,
                        "Employee references a missing location.",
                        employee.location_id,
                    )
                )

            if (
                employee.manager_employee_id
                and employee.manager_employee_id not in employees
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "missing_reference",
                        employee.employee_id,
                        "Employee references a missing manager.",
                        employee.manager_employee_id,
                    )
                )

            if (
                employee.department_id in departments
                and employee.organization_id
                and departments[employee.department_id].organization_id
                != employee.organization_id
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "organization_mismatch",
                        employee.employee_id,
                        "Employee and department belong to different organizations.",
                        employee.department_id,
                    )
                )

            if (
                employee.team_id in teams
                and employee.organization_id
                and teams[employee.team_id].organization_id
                != employee.organization_id
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "organization_mismatch",
                        employee.employee_id,
                        "Employee and team belong to different organizations.",
                        employee.team_id,
                    )
                )

            if (
                employee.location_id in locations
                and employee.organization_id
                and locations[employee.location_id].organization_id
                != employee.organization_id
            ):
                issues.append(
                    OrganizationValidationIssue(
                        "organization_mismatch",
                        employee.employee_id,
                        "Employee and location belong to different organizations.",
                        employee.location_id,
                    )
                )

        return issues

    @staticmethod
    def _duplicate_id_issues(
        node_type: str,
        ids: list[str],
    ) -> list[OrganizationValidationIssue]:
        seen: set[str] = set()
        duplicates: set[str] = set()

        for node_id in ids:
            if node_id in seen:
                duplicates.add(node_id)
            seen.add(node_id)

        return [
            OrganizationValidationIssue(
                "duplicate_id",
                node_id,
                f"Duplicate {node_type} ID detected.",
            )
            for node_id in sorted(duplicates)
        ]
