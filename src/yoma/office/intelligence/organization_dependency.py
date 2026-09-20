from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OrganizationalDependencySignal:
    member_id: str
    dependent_member_count: int
    workload: float
    workload_ratio: float
    dependency_level: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class OrganizationalDependencyResult:
    organization_id: str
    total_members: int
    dependency_signals: tuple[OrganizationalDependencySignal, ...]
    critical_dependency_count: int
    elevated_dependency_count: int
    normal_dependency_count: int
    dependency_rate: float
    maximum_dependent_member_count: int
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class OrganizationalDependencyRuntime:
    """
    M36.6 — Organizational Dependency & Continuity Analysis.

    Read-only analysis of organizational dependency concentration.

    No execution.
    No approval.
    No mutation.
    No automatic reassignment or repair.
    """

    def analyze(
        self,
        members: Iterable[object],
        workload_by_member: dict[str, float],
        *,
        organization_id: str,
        critical_dependents: int = 5,
        elevated_dependents: int = 2,
        high_workload_ratio: float = 2.0,
    ) -> OrganizationalDependencyResult:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id must be non-empty")

        if critical_dependents < 1:
            raise ValueError("critical_dependents must be >= 1")

        if elevated_dependents < 1:
            raise ValueError("elevated_dependents must be >= 1")

        if elevated_dependents > critical_dependents:
            raise ValueError(
                "elevated_dependents must be <= critical_dependents"
            )

        if high_workload_ratio <= 0:
            raise ValueError("high_workload_ratio must be > 0")

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

        for member_id in member_map:
            normalized_workload.setdefault(member_id, 0.0)

        normalized_workload = dict(
            sorted(normalized_workload.items())
        )

        total_workload = sum(normalized_workload.values())
        average_workload = (
            total_workload / len(member_map)
            if member_map
            else 0.0
        )

        dependents: dict[str, list[str]] = {}

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

                dependents.setdefault(manager_id, []).append(member_id)

        signals: list[OrganizationalDependencySignal] = []

        for member_id in sorted(member_map):
            dependent_ids = tuple(
                sorted(dependents.get(member_id, []))
            )
            dependent_count = len(dependent_ids)

            workload = normalized_workload[member_id]

            workload_ratio = (
                workload / average_workload
                if average_workload > 0
                else 0.0
            )

            reasons: list[str] = []

            if dependent_count >= critical_dependents:
                dependency_level = "critical"
                reasons.append("high_reporting_dependency")
            elif dependent_count >= elevated_dependents:
                dependency_level = "elevated"
                reasons.append("reporting_dependency")
            else:
                dependency_level = "normal"

            if workload_ratio >= high_workload_ratio:
                reasons.append("high_workload_concentration")

            signals.append(
                OrganizationalDependencySignal(
                    member_id=member_id,
                    dependent_member_count=dependent_count,
                    workload=workload,
                    workload_ratio=workload_ratio,
                    dependency_level=dependency_level,
                    reasons=tuple(sorted(reasons)),
                )
            )

        # Highest dependency first, then workload concentration,
        # then deterministic member ID ordering.
        signals.sort(
            key=lambda signal: (
                -signal.dependent_member_count,
                -signal.workload_ratio,
                signal.member_id,
            )
        )

        critical_count = sum(
            signal.dependency_level == "critical"
            for signal in signals
        )

        elevated_count = sum(
            signal.dependency_level == "elevated"
            for signal in signals
        )

        normal_count = sum(
            signal.dependency_level == "normal"
            for signal in signals
        )

        dependency_rate = (
            (critical_count + elevated_count) / len(member_map)
            if member_map
            else 0.0
        )

        maximum_dependents = max(
            (
                signal.dependent_member_count
                for signal in signals
            ),
            default=0,
        )

        return OrganizationalDependencyResult(
            organization_id=organization_id,
            total_members=len(member_map),
            dependency_signals=tuple(signals),
            critical_dependency_count=critical_count,
            elevated_dependency_count=elevated_count,
            normal_dependency_count=normal_count,
            dependency_rate=dependency_rate,
            maximum_dependent_member_count=maximum_dependents,
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.6",
                "analytics_only": True,
                "continuity_analysis_only": True,
                "read_only": True,
                "executable": False,
                "automatic_reassignment": False,
            },
        )
