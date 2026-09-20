from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WorkloadDistribution:
    organization_id: str
    total_members: int
    workload_by_member: dict[str, float]
    workload_by_manager: dict[str, float]
    workload_by_department: dict[str, float]
    workload_by_team: dict[str, float]
    average_member_workload: float
    maximum_member_workload: float
    minimum_member_workload: float
    workload_concentration_rate: float
    overloaded_members: tuple[str, ...]
    workload_threshold: float
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class OrganizationalWorkloadRuntime:
    """
    M36.4 — Organizational Workload Distribution.

    Read-only analytical layer over organizational members and
    externally supplied workload observations.

    No execution.
    No approval.
    No mutation.
    """

    def analyze(
        self,
        members: Iterable[object],
        workload_by_member: dict[str, float],
        *,
        organization_id: str,
        workload_threshold: float = 1.0,
    ) -> WorkloadDistribution:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id must be non-empty")

        if workload_threshold < 0:
            raise ValueError("workload_threshold must be >= 0")

        items = tuple(members)
        member_map: dict[str, object] = {}

        for member in items:
            if not hasattr(member, "member_id"):
                raise TypeError(
                    "members must contain OrganizationMember-compatible objects"
                )

            member_org = str(
                getattr(member, "organization_id", "")
            ).strip()

            if member_org != organization_id:
                raise ValueError(
                    "all members must belong to the requested organization"
                )

            member_id = str(
                getattr(member, "member_id", "")
            ).strip()

            if not member_id:
                raise ValueError("member_id must be non-empty")

            if member_id in member_map:
                raise ValueError(f"duplicate member_id: {member_id}")

            member_map[member_id] = member

        normalized_workload: dict[str, float] = {}

        for member_id, value in workload_by_member.items():
            member_id = str(member_id).strip()

            if member_id not in member_map:
                raise ValueError(
                    f"workload supplied for unknown member: {member_id}"
                )

            try:
                workload = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"workload for {member_id} must be numeric"
                ) from exc

            if workload < 0:
                raise ValueError(
                    f"workload for {member_id} must be >= 0"
                )

            normalized_workload[member_id] = workload

        # Members without an observation are represented as zero workload.
        for member_id in member_map:
            normalized_workload.setdefault(member_id, 0.0)

        normalized_workload = dict(
            sorted(normalized_workload.items())
        )

        department_totals: dict[str, float] = {}
        team_totals: dict[str, float] = {}
        manager_totals: dict[str, float] = {}

        for member_id, workload in normalized_workload.items():
            member = member_map[member_id]

            department = str(
                getattr(member, "department", "") or ""
            ).strip()

            team = str(
                getattr(member, "team", "") or ""
            ).strip()

            manager_id = str(
                getattr(member, "manager_id", "") or ""
            ).strip()

            if department:
                department_totals[department] = (
                    department_totals.get(department, 0.0) + workload
                )

            if team:
                team_totals[team] = (
                    team_totals.get(team, 0.0) + workload
                )

            if manager_id:
                manager_totals[manager_id] = (
                    manager_totals.get(manager_id, 0.0) + workload
                )

        department_totals = dict(sorted(department_totals.items()))
        team_totals = dict(sorted(team_totals.items()))
        manager_totals = dict(sorted(manager_totals.items()))

        values = tuple(normalized_workload.values())
        total_workload = sum(values)

        if values:
            average_workload = total_workload / len(values)
            maximum_workload = max(values)
            minimum_workload = min(values)
        else:
            average_workload = 0.0
            maximum_workload = 0.0
            minimum_workload = 0.0

        overloaded_members = tuple(
            member_id
            for member_id, workload in normalized_workload.items()
            if workload >= workload_threshold
        )

        # Share of total workload held by the highest-workload member.
        if total_workload > 0:
            workload_concentration_rate = (
                maximum_workload / total_workload
            )
        else:
            workload_concentration_rate = 0.0

        return WorkloadDistribution(
            organization_id=organization_id,
            total_members=len(member_map),
            workload_by_member=normalized_workload,
            workload_by_manager=manager_totals,
            workload_by_department=department_totals,
            workload_by_team=team_totals,
            average_member_workload=average_workload,
            maximum_member_workload=maximum_workload,
            minimum_member_workload=minimum_workload,
            workload_concentration_rate=workload_concentration_rate,
            overloaded_members=overloaded_members,
            workload_threshold=workload_threshold,
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.4",
                "analytics_only": True,
                "read_only": True,
                "executable": False,
                "observed_workload_not_modified": True,
            },
        )
