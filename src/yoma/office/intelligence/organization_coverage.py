from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OrganizationalCoverageSignal:
    member_id: str
    dependent_member_count: int
    has_manager: bool
    is_manager: bool
    manager_has_backup: bool
    coverage_level: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class OrganizationalCoverageResult:
    organization_id: str
    total_members: int
    managers: tuple[str, ...]
    uncovered_members: tuple[str, ...]
    single_point_managers: tuple[str, ...]
    covered_members: int
    coverage_rate: float
    signals: tuple[OrganizationalCoverageSignal, ...]
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class OrganizationalCoverageRuntime:
    """
    M36.7 — Organizational Continuity & Coverage Analysis.

    Read-only analysis of reporting coverage and structural
    continuity.

    No reassignment.
    No execution.
    No approval.
    No mutation.
    """

    def analyze(
        self,
        members: Iterable[object],
        *,
        organization_id: str,
    ) -> OrganizationalCoverageResult:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id must be non-empty")

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

        manager_by_member: dict[str, str] = {}
        direct_reports: dict[str, list[str]] = {}

        for member_id, member in member_map.items():
            manager_id = str(
                getattr(member, "manager_id", "") or ""
            ).strip()

            if manager_id:
                if manager_id not in member_map:
                    raise ValueError(
                        f"manager_id {manager_id} for {member_id} "
                        "does not reference a known member"
                    )

                manager_by_member[member_id] = manager_id
                direct_reports.setdefault(manager_id, []).append(member_id)

        managers = tuple(sorted(direct_reports))
        uncovered_members = tuple(
            sorted(
                member_id
                for member_id in member_map
                if member_id not in manager_by_member
            )
        )

        # A manager with multiple direct reports has structural
        # coverage through more than one dependent relationship.
        # A manager with exactly one direct report is treated as a
        # potential single-point relationship.
        single_point_managers = tuple(
            sorted(
                manager_id
                for manager_id, reports in direct_reports.items()
                if len(reports) == 1
            )
        )

        signals: list[OrganizationalCoverageSignal] = []

        for member_id in sorted(member_map):
            dependent_count = len(
                direct_reports.get(member_id, [])
            )

            has_manager = member_id in manager_by_member
            is_manager = dependent_count > 0

            manager_has_backup = dependent_count >= 2

            reasons: list[str] = []

            if not has_manager:
                reasons.append("no_manager")

            if is_manager and dependent_count == 1:
                reasons.append("single_reporting_dependency")

            if is_manager and dependent_count >= 2:
                reasons.append("multiple_direct_reports")

            if not has_manager and not is_manager:
                coverage_level = "uncovered"
            elif is_manager and dependent_count == 1:
                coverage_level = "single_point"
            else:
                coverage_level = "covered"

            signals.append(
                OrganizationalCoverageSignal(
                    member_id=member_id,
                    dependent_member_count=dependent_count,
                    has_manager=has_manager,
                    is_manager=is_manager,
                    manager_has_backup=manager_has_backup,
                    coverage_level=coverage_level,
                    reasons=tuple(sorted(reasons)),
                )
            )

        signals.sort(
            key=lambda signal: (
                {
                    "uncovered": 0,
                    "single_point": 1,
                    "covered": 2,
                }[signal.coverage_level],
                signal.member_id,
            )
        )

        covered_members = sum(
            signal.coverage_level == "covered"
            for signal in signals
        )

        coverage_rate = (
            covered_members / len(member_map)
            if member_map
            else 0.0
        )

        return OrganizationalCoverageResult(
            organization_id=organization_id,
            total_members=len(member_map),
            managers=managers,
            uncovered_members=uncovered_members,
            single_point_managers=single_point_managers,
            covered_members=covered_members,
            coverage_rate=coverage_rate,
            signals=tuple(signals),
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.7",
                "analytics_only": True,
                "continuity_analysis_only": True,
                "read_only": True,
                "executable": False,
                "automatic_reassignment": False,
            },
        )
