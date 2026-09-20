from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WorkloadRiskSignal:
    entity_id: str
    entity_type: str
    workload: float
    average_workload: float
    workload_ratio: float
    risk_level: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class OrganizationalWorkloadRiskResult:
    organization_id: str
    total_members: int
    total_workload: float
    average_workload: float
    signals: tuple[WorkloadRiskSignal, ...]
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    risk_rate: float
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class OrganizationalWorkloadRiskRuntime:
    """
    M36.5 — Organizational Workload Risk & Dependency Analysis.

    Derives workload concentration and organizational dependency
    risk from existing OrganizationMember records and workload
    observations.

    Read-only.
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
        high_risk_ratio: float = 2.0,
        medium_risk_ratio: float = 1.5,
    ) -> OrganizationalWorkloadRiskResult:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id must be non-empty")

        if high_risk_ratio <= 0:
            raise ValueError("high_risk_ratio must be > 0")

        if medium_risk_ratio <= 0:
            raise ValueError("medium_risk_ratio must be > 0")

        if medium_risk_ratio > high_risk_ratio:
            raise ValueError(
                "medium_risk_ratio must be <= high_risk_ratio"
            )

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

        normalized: dict[str, float] = {}

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

            normalized[member_id] = workload

        for member_id in member_map:
            normalized.setdefault(member_id, 0.0)

        normalized = dict(sorted(normalized.items()))

        total_workload = sum(normalized.values())
        total_members = len(member_map)

        average_workload = (
            total_workload / total_members
            if total_members
            else 0.0
        )

        signals: list[WorkloadRiskSignal] = []

        for member_id, workload in normalized.items():
            if average_workload > 0:
                ratio = workload / average_workload
            else:
                ratio = 0.0

            if ratio >= high_risk_ratio:
                risk_level = "high"
            elif ratio >= medium_risk_ratio:
                risk_level = "medium"
            else:
                risk_level = "low"

            reasons: list[str] = []

            if ratio >= high_risk_ratio:
                reasons.append("workload_significantly_above_average")
            elif ratio >= medium_risk_ratio:
                reasons.append("workload_above_average")

            manager_id = str(
                getattr(member_map[member_id], "manager_id", "") or ""
            ).strip()

            if manager_id:
                manager_workload = normalized.get(manager_id)

                if (
                    manager_workload is not None
                    and average_workload > 0
                    and manager_workload / average_workload >= high_risk_ratio
                ):
                    reasons.append("manager_workload_concentration")

            signals.append(
                WorkloadRiskSignal(
                    entity_id=member_id,
                    entity_type="member",
                    workload=workload,
                    average_workload=average_workload,
                    workload_ratio=ratio,
                    risk_level=risk_level,
                    reasons=tuple(sorted(reasons)),
                )
            )

        signals.sort(
            key=lambda item: (
                -item.workload_ratio,
                item.entity_type,
                item.entity_id,
            )
        )

        high_risk_count = sum(
            signal.risk_level == "high"
            for signal in signals
        )

        medium_risk_count = sum(
            signal.risk_level == "medium"
            for signal in signals
        )

        low_risk_count = sum(
            signal.risk_level == "low"
            for signal in signals
        )

        risk_rate = (
            (high_risk_count + medium_risk_count) / total_members
            if total_members
            else 0.0
        )

        return OrganizationalWorkloadRiskResult(
            organization_id=organization_id,
            total_members=total_members,
            total_workload=total_workload,
            average_workload=average_workload,
            signals=tuple(signals),
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            risk_rate=risk_rate,
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.5",
                "analytics_only": True,
                "risk_estimate_only": True,
                "read_only": True,
                "executable": False,
            },
        )
