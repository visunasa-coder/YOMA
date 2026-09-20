from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OrganizationalRelationship:
    member_id: str
    manager_id: str
    relationship_type: str = "reports_to"
    organization_id: str = ""
    metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class WorkforceStructureResult:
    organization_id: str
    total_members: int
    direct_reports: dict[str, tuple[str, ...]]
    managers_by_member: dict[str, str]
    manager_count: int
    relationship_count: int
    departments_by_member: dict[str, str]
    teams_by_member: dict[str, str]
    locations_by_member: dict[str, str]
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class WorkforceStructureRuntime:
    """
    M36.2 — Workforce Structure & Organizational Relationships.

    Read-only intelligence over OrganizationMember records.

    This runtime:
    - derives manager/reporting relationships
    - derives member department/team/location mappings
    - provides deterministic organizational structure
    - does not mutate organization state
    - does not execute actions
    - does not create approval workflows
    """

    def analyze(
        self,
        members: Iterable[object],
        *,
        organization_id: str,
    ) -> WorkforceStructureResult:
        organization_id = str(organization_id).strip()
        if not organization_id:
            raise ValueError("organization_id must be non-empty")

        items = tuple(members)

        normalized: list[object] = []
        member_ids: set[str] = set()

        for member in items:
            if not hasattr(member, "member_id"):
                raise TypeError(
                    "members must contain OrganizationMember-compatible objects"
                )

            member_org = str(getattr(member, "organization_id", "")).strip()
            if member_org != organization_id:
                raise ValueError(
                    "all members must belong to the requested organization"
                )

            member_id = str(getattr(member, "member_id", "")).strip()
            if not member_id:
                raise ValueError("member_id must be non-empty")

            if member_id in member_ids:
                raise ValueError(f"duplicate member_id: {member_id}")

            member_ids.add(member_id)
            normalized.append(member)

        managers_by_member: dict[str, str] = {}
        direct_reports: dict[str, list[str]] = {}

        departments_by_member: dict[str, str] = {}
        teams_by_member: dict[str, str] = {}
        locations_by_member: dict[str, str] = {}

        for member in normalized:
            member_id = str(member.member_id).strip()

            manager_id = str(getattr(member, "manager_id", "") or "").strip()
            department = str(getattr(member, "department", "") or "").strip()
            team = str(getattr(member, "team", "") or "").strip()
            location = str(getattr(member, "location", "") or "").strip()

            if manager_id:
                managers_by_member[member_id] = manager_id
                direct_reports.setdefault(manager_id, []).append(member_id)

            if department:
                departments_by_member[member_id] = department

            if team:
                teams_by_member[member_id] = team

            if location:
                locations_by_member[member_id] = location

        frozen_reports = {
            manager_id: tuple(sorted(reports))
            for manager_id, reports in sorted(direct_reports.items())
        }

        return WorkforceStructureResult(
            organization_id=organization_id,
            total_members=len(normalized),
            direct_reports=frozen_reports,
            managers_by_member=dict(sorted(managers_by_member.items())),
            manager_count=len(frozen_reports),
            relationship_count=len(managers_by_member),
            departments_by_member=dict(sorted(departments_by_member.items())),
            teams_by_member=dict(sorted(teams_by_member.items())),
            locations_by_member=dict(sorted(locations_by_member.items())),
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.2",
                "analytics_only": True,
                "read_only": True,
                "executable": False,
            },
        )
