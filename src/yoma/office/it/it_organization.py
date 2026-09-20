"""YOMA IT Edition — canonical IT organization model.

Read-only domain representation for software/IT organizations.
This module provides intelligence input structures only.

Safety:
- No execution.
- No autonomous authorization.
- No mutation of external systems.
- Recommendations remain governed by the existing approval boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_ALLOWED_ROLES = {
    "employee",
    "developer",
    "engineer",
    "devops",
    "qa",
    "support",
    "helpdesk",
    "project_manager",
    "product_manager",
    "team_lead",
    "engineering_manager",
    "architect",
    "admin",
    "executive",
}


@dataclass(frozen=True)
class ITMember:
    member_id: str
    organization_id: str
    name: str
    role: str
    team_id: str | None = None
    manager_id: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "member_id",
            "organization_id",
            "name",
            "role",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.team_id is not None and (
            not isinstance(self.team_id, str) or not self.team_id.strip()
        ):
            raise ValueError("team_id must be a non-empty string when provided")

        if self.manager_id is not None and (
            not isinstance(self.manager_id, str) or not self.manager_id.strip()
        ):
            raise ValueError("manager_id must be a non-empty string when provided")

        normalized_role = self.role.strip().lower()
        if normalized_role not in _ALLOWED_ROLES:
            raise ValueError(f"unsupported IT role: {self.role}")

        if not isinstance(self.active, bool):
            raise ValueError("active must be boolean")


@dataclass(frozen=True)
class ITTeam:
    team_id: str
    organization_id: str
    name: str
    function: str
    manager_id: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "team_id",
            "organization_id",
            "name",
            "function",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.manager_id is not None and (
            not isinstance(self.manager_id, str) or not self.manager_id.strip()
        ):
            raise ValueError("manager_id must be a non-empty string when provided")

        if not isinstance(self.active, bool):
            raise ValueError("active must be boolean")


@dataclass(frozen=True)
class ITService:
    service_id: str
    organization_id: str
    name: str
    owner_team_id: str | None = None
    criticality: str = "normal"
    active: bool = True

    def __post_init__(self) -> None:
        for field_name in ("service_id", "organization_id", "name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.owner_team_id is not None and (
            not isinstance(self.owner_team_id, str)
            or not self.owner_team_id.strip()
        ):
            raise ValueError("owner_team_id must be a non-empty string when provided")

        if self.criticality not in {"low", "normal", "high", "critical"}:
            raise ValueError("criticality must be low, normal, high, or critical")

        if not isinstance(self.active, bool):
            raise ValueError("active must be boolean")


@dataclass(frozen=True)
class ITOrganization:
    organization_id: str
    name: str
    members: tuple[ITMember, ...] = ()
    teams: tuple[ITTeam, ...] = ()
    services: tuple[ITService, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.organization_id, str) or not self.organization_id.strip():
            raise ValueError("organization_id must be a non-empty string")

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")

        if not isinstance(self.members, tuple):
            raise ValueError("members must be a tuple")

        if not isinstance(self.teams, tuple):
            raise ValueError("teams must be a tuple")

        if not isinstance(self.services, tuple):
            raise ValueError("services must be a tuple")

        if any(member.organization_id != self.organization_id for member in self.members):
            raise ValueError("all members must belong to the organization")

        if any(team.organization_id != self.organization_id for team in self.teams):
            raise ValueError("all teams must belong to the organization")

        if any(service.organization_id != self.organization_id for service in self.services):
            raise ValueError("all services must belong to the organization")

    @property
    def active_members(self) -> tuple[ITMember, ...]:
        return tuple(member for member in self.members if member.active)

    @property
    def active_teams(self) -> tuple[ITTeam, ...]:
        return tuple(team for team in self.teams if team.active)

    @property
    def active_services(self) -> tuple[ITService, ...]:
        return tuple(service for service in self.services if service.active)

    def team_members(self, team_id: str) -> tuple[ITMember, ...]:
        return tuple(
            member
            for member in self.members
            if member.team_id == team_id and member.active
        )

    def service_owner(self, service_id: str) -> ITTeam | None:
        for team in self.teams:
            if team.team_id == service_id:
                return team
        service = next(
            (item for item in self.services if item.service_id == service_id),
            None,
        )
        if service is None or service.owner_team_id is None:
            return None
        return next(
            (team for team in self.teams if team.team_id == service.owner_team_id),
            None,
        )


@dataclass(frozen=True)
class ITOrganizationAnalysis:
    organization_id: str
    member_count: int
    active_member_count: int
    team_count: int
    active_team_count: int
    service_count: int
    active_service_count: int
    critical_service_count: int
    unassigned_members: int
    unmanaged_members: int
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


class ITOrganizationIntelligence:
    """Read-only IT organization analyzer."""

    def analyze(self, organization: ITOrganization) -> ITOrganizationAnalysis:
        if not isinstance(organization, ITOrganization):
            raise TypeError("organization must be ITOrganization")

        issues: list[str] = []

        unassigned_members = sum(
            1
            for member in organization.active_members
            if member.team_id is None
        )

        unmanaged_members = sum(
            1
            for member in organization.active_members
            if member.manager_id is None
            and member.role.strip().lower() not in {"executive", "admin"}
        )

        critical_service_count = sum(
            1
            for service in organization.active_services
            if service.criticality == "critical"
        )

        if unassigned_members:
            issues.append("active members without team assignment")

        if unmanaged_members:
            issues.append("active members without manager assignment")

        if critical_service_count:
            issues.append("critical IT services require operational ownership validation")

        return ITOrganizationAnalysis(
            organization_id=organization.organization_id,
            member_count=len(organization.members),
            active_member_count=len(organization.active_members),
            team_count=len(organization.teams),
            active_team_count=len(organization.active_teams),
            service_count=len(organization.services),
            active_service_count=len(organization.active_services),
            critical_service_count=critical_service_count,
            unassigned_members=unassigned_members,
            unmanaged_members=unmanaged_members,
            issues=tuple(issues),
        )


def analyze_it_organization(
    organization: ITOrganization,
) -> ITOrganizationAnalysis:
    return ITOrganizationIntelligence().analyze(organization)
