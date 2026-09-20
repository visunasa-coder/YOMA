from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class OrganizationMember:
    """Read-only representation of a member in an organization."""

    member_id: str
    organization_id: str
    department: str | None = None
    team: str | None = None
    location: str | None = None
    manager_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OrganizationIntelligenceResult:
    """Deterministic organization/workforce intelligence snapshot."""

    organization_id: str
    total_members: int
    departments: tuple[str, ...]
    teams: tuple[str, ...]
    locations: tuple[str, ...]
    managers: tuple[str, ...]
    members_by_department: Mapping[str, int]
    members_by_team: Mapping[str, int]
    members_by_location: Mapping[str, int]
    reporting_relationships: Mapping[str, tuple[str, ...]]
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)


class OrganizationIntelligenceRuntime:
    """Build a read-only organization intelligence snapshot."""

    def analyze(
        self,
        organization_id: str,
        members: tuple[OrganizationMember, ...] | list[OrganizationMember],
    ) -> OrganizationIntelligenceResult:
        if not isinstance(organization_id, str) or not organization_id.strip():
            raise ValueError("organization_id must be a non-empty string")

        normalized = tuple(members)

        for member in normalized:
            if not isinstance(member, OrganizationMember):
                raise TypeError(
                    "members must contain OrganizationMember instances"
                )

            if member.organization_id != organization_id:
                raise ValueError(
                    "all members must belong to the requested organization"
                )

            if not member.member_id.strip():
                raise ValueError("member_id must be non-empty")

        departments = sorted(
            {
                member.department
                for member in normalized
                if member.department
            }
        )

        teams = sorted(
            {
                member.team
                for member in normalized
                if member.team
            }
        )

        locations = sorted(
            {
                member.location
                for member in normalized
                if member.location
            }
        )

        managers = sorted(
            {
                member.manager_id
                for member in normalized
                if member.manager_id
            }
        )

        members_by_department = {
            department: sum(
                member.department == department
                for member in normalized
            )
            for department in departments
        }

        members_by_team = {
            team: sum(
                member.team == team
                for member in normalized
            )
            for team in teams
        }

        members_by_location = {
            location: sum(
                member.location == location
                for member in normalized
            )
            for location in locations
        }

        relationships: dict[str, list[str]] = {}

        for member in normalized:
            if member.manager_id:
                relationships.setdefault(member.manager_id, []).append(
                    member.member_id
                )

        reporting_relationships = {
            manager_id: tuple(sorted(member_ids))
            for manager_id, member_ids in sorted(relationships.items())
        }

        return OrganizationIntelligenceResult(
            organization_id=organization_id,
            total_members=len(normalized),
            departments=tuple(departments),
            teams=tuple(teams),
            locations=tuple(locations),
            managers=tuple(managers),
            members_by_department=members_by_department,
            members_by_team=members_by_team,
            members_by_location=members_by_location,
            reporting_relationships=reporting_relationships,
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.1",
                "organization_intelligence": True,
                "analytics_only": True,
                "composition_only": True,
                "read_only": True,
                "executable": False,
            },
        )
