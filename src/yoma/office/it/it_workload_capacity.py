from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_VALID_PRIORITIES = {"low", "normal", "high", "critical"}
_VALID_STATUSES = {
    "backlog",
    "planned",
    "in_progress",
    "blocked",
    "completed",
    "cancelled",
}


def _require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_non_negative(value: float | int, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return float(value)


@dataclass(frozen=True)
class ITWorkload:
    workload_id: str
    organization_id: str
    member_id: str | None = None
    team_id: str | None = None
    project_id: str | None = None
    service_id: str | None = None
    title: str = ""
    estimated_hours: float = 0.0
    priority: str = "normal"
    status: str = "backlog"

    def __post_init__(self) -> None:
        _require_text(self.workload_id, "workload_id")
        _require_text(self.organization_id, "organization_id")

        if self.member_id is not None:
            _require_text(self.member_id, "member_id")
        if self.team_id is not None:
            _require_text(self.team_id, "team_id")
        if self.project_id is not None:
            _require_text(self.project_id, "project_id")
        if self.service_id is not None:
            _require_text(self.service_id, "service_id")

        if not isinstance(self.title, str):
            raise ValueError("title must be a string")

        _require_non_negative(self.estimated_hours, "estimated_hours")

        if self.priority not in _VALID_PRIORITIES:
            raise ValueError(f"invalid priority: {self.priority}")

        if self.status not in _VALID_STATUSES:
            raise ValueError(f"invalid status: {self.status}")


@dataclass(frozen=True)
class ITCapacity:
    member_id: str
    organization_id: str
    team_id: str | None = None
    available_hours: float = 0.0

    def __post_init__(self) -> None:
        _require_text(self.member_id, "member_id")
        _require_text(self.organization_id, "organization_id")

        if self.team_id is not None:
            _require_text(self.team_id, "team_id")

        _require_non_negative(self.available_hours, "available_hours")


@dataclass(frozen=True)
class ITWorkloadCapacityPortfolio:
    organization_id: str
    workloads: tuple[ITWorkload, ...] = ()
    capacities: tuple[ITCapacity, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.organization_id, "organization_id")

        if not isinstance(self.workloads, tuple):
            raise ValueError("workloads must be a tuple")

        if not isinstance(self.capacities, tuple):
            raise ValueError("capacities must be a tuple")

        for workload in self.workloads:
            if not isinstance(workload, ITWorkload):
                raise ValueError("workloads must contain ITWorkload instances")
            if workload.organization_id != self.organization_id:
                raise ValueError("workload organization_id mismatch")

        for capacity in self.capacities:
            if not isinstance(capacity, ITCapacity):
                raise ValueError("capacities must contain ITCapacity instances")
            if capacity.organization_id != self.organization_id:
                raise ValueError("capacity organization_id mismatch")


@dataclass(frozen=True)
class ITWorkloadCapacityAnalysis:
    organization_id: str
    workload_count: int
    active_workload_count: int
    completed_workload_count: int
    blocked_workload_count: int
    unassigned_workload_count: int
    high_priority_workload_count: int
    capacity_member_count: int
    total_available_hours: float
    total_assigned_hours: float
    capacity_shortfall_hours: float
    overloaded_member_count: int
    underutilized_member_count: int
    workload_concentration_member_id: str | None
    workload_concentration_hours: float
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


@dataclass(frozen=True)
class ITWorkloadCapacityIntelligence:
    """
    Read-only workload and capacity intelligence for IT organizations.

    This class observes workload/capacity state and produces analytical
    findings only. It does not assign work, rebalance teams, change
    priorities, modify tickets, or execute any operational action.
    """

    overload_threshold: float = 1.0
    underutilization_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.overload_threshold, (int, float)):
            raise ValueError("overload_threshold must be numeric")
        if not 0 < self.overload_threshold:
            raise ValueError("overload_threshold must be greater than zero")

        if not isinstance(self.underutilization_threshold, (int, float)):
            raise ValueError("underutilization_threshold must be numeric")
        if not 0 <= self.underutilization_threshold < 1:
            raise ValueError(
                "underutilization_threshold must be between 0 and 1"
            )

    def analyze(
        self,
        portfolio: ITWorkloadCapacityPortfolio,
    ) -> ITWorkloadCapacityAnalysis:
        if not isinstance(portfolio, ITWorkloadCapacityPortfolio):
            raise TypeError("portfolio must be ITWorkloadCapacityPortfolio")

        workloads = tuple(
            sorted(
                portfolio.workloads,
                key=lambda item: item.workload_id,
            )
        )
        capacities = tuple(
            sorted(
                portfolio.capacities,
                key=lambda item: item.member_id,
            )
        )

        active = tuple(
            item
            for item in workloads
            if item.status not in {"completed", "cancelled"}
        )

        assigned = tuple(
            item
            for item in active
            if item.member_id is not None
        )

        completed = sum(
            1 for item in workloads if item.status == "completed"
        )
        blocked = sum(
            1 for item in active if item.status == "blocked"
        )
        unassigned = sum(
            1 for item in active if item.member_id is None
        )
        high_priority = sum(
            1
            for item in active
            if item.priority in {"high", "critical"}
        )

        total_available = sum(
            item.available_hours for item in capacities
        )
        total_assigned = sum(
            item.estimated_hours for item in assigned
        )

        shortfall = max(
            0.0,
            total_assigned - total_available,
        )

        capacity_by_member = {
            item.member_id: item.available_hours
            for item in capacities
        }

        workload_by_member: dict[str, float] = {}

        for item in assigned:
            workload_by_member[item.member_id] = (
                workload_by_member.get(item.member_id, 0.0)
                + item.estimated_hours
            )

        overloaded = 0
        underutilized = 0

        for member_id, available in capacity_by_member.items():
            workload_hours = workload_by_member.get(member_id, 0.0)

            if available == 0:
                if workload_hours > 0:
                    overloaded += 1
                continue

            utilization = workload_hours / available

            if utilization > self.overload_threshold:
                overloaded += 1
            elif utilization < self.underutilization_threshold:
                underutilized += 1

        concentration_member_id = None
        concentration_hours = 0.0

        if workload_by_member:
            concentration_member_id, concentration_hours = max(
                workload_by_member.items(),
                key=lambda item: (item[1], item[0]),
            )

        issues: list[str] = []

        if unassigned:
            issues.append(
                f"{unassigned} active workloads have no assigned owner"
            )

        if blocked:
            issues.append(
                f"{blocked} active workloads are blocked"
            )

        if high_priority:
            issues.append(
                f"{high_priority} active workloads have high or critical priority"
            )

        if shortfall > 0:
            issues.append(
                f"estimated assigned workload exceeds available capacity by "
                f"{shortfall:g} hours"
            )

        if overloaded:
            issues.append(
                f"{overloaded} members exceed the configured workload capacity threshold"
            )

        if underutilized:
            issues.append(
                f"{underutilized} members are below the configured utilization threshold"
            )

        if concentration_member_id is not None and total_assigned > 0:
            concentration_ratio = (
                concentration_hours / total_assigned
            )

            if concentration_ratio >= 0.5:
                issues.append(
                    f"workload is concentrated on member "
                    f"{concentration_member_id}"
                )

        return ITWorkloadCapacityAnalysis(
            organization_id=portfolio.organization_id,
            workload_count=len(workloads),
            active_workload_count=len(active),
            completed_workload_count=completed,
            blocked_workload_count=blocked,
            unassigned_workload_count=unassigned,
            high_priority_workload_count=high_priority,
            capacity_member_count=len(capacities),
            total_available_hours=total_available,
            total_assigned_hours=total_assigned,
            capacity_shortfall_hours=shortfall,
            overloaded_member_count=overloaded,
            underutilized_member_count=underutilized,
            workload_concentration_member_id=concentration_member_id,
            workload_concentration_hours=concentration_hours,
            issues=tuple(issues),
            requires_human_approval=True,
            executable=False,
        )


def analyze_it_workload_capacity(
    portfolio: ITWorkloadCapacityPortfolio,
) -> ITWorkloadCapacityAnalysis:
    return ITWorkloadCapacityIntelligence().analyze(portfolio)
