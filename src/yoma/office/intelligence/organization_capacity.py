from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OrganizationalCapacityResult:
    organization_id: str
    total_members: int
    manager_count: int
    managed_member_count: int
    unmanaged_member_count: int
    average_span_of_control: float
    minimum_span_of_control: int
    maximum_span_of_control: int
    spans_by_manager: dict[str, int]
    unmanaged_members: tuple[str, ...]
    hierarchy_depth: int
    overloaded_managers: tuple[str, ...]
    capacity_threshold: int
    read_only: bool = True
    executable: bool = False
    metadata: dict[str, object] | None = None


class OrganizationalCapacityRuntime:
    """
    M36.3 — Organizational Capacity & Span Analysis.

    Read-only analytical layer over OrganizationMember records.

    No execution.
    No approval.
    No mutation.
    No policy modification.
    """

    def analyze(
        self,
        members: Iterable[object],
        *,
        organization_id: str,
        capacity_threshold: int = 10,
    ) -> OrganizationalCapacityResult:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id must be non-empty")

        if capacity_threshold < 1:
            raise ValueError("capacity_threshold must be >= 1")

        items = tuple(members)
        member_ids: set[str] = set()
        manager_by_member: dict[str, str] = {}

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

            if member_id in member_ids:
                raise ValueError(f"duplicate member_id: {member_id}")

            member_ids.add(member_id)

            manager_id = str(
                getattr(member, "manager_id", "") or ""
            ).strip()

            if manager_id:
                manager_by_member[member_id] = manager_id

        spans: dict[str, int] = {}

        for manager_id in manager_by_member.values():
            spans[manager_id] = spans.get(manager_id, 0) + 1

        spans = dict(sorted(spans.items()))

        managed_member_count = len(manager_by_member)
        unmanaged_members = tuple(
            sorted(member_ids - set(manager_by_member))
        )

        manager_count = len(spans)
        total_members = len(member_ids)
        unmanaged_member_count = len(unmanaged_members)

        if spans:
            span_values = tuple(spans.values())
            average_span = sum(span_values) / len(span_values)
            minimum_span = min(span_values)
            maximum_span = max(span_values)
        else:
            average_span = 0.0
            minimum_span = 0
            maximum_span = 0

        overloaded_managers = tuple(
            manager_id
            for manager_id, span in spans.items()
            if span >= capacity_threshold
        )

        # Derive hierarchy depth from member -> manager chains.
        manager_lookup = dict(manager_by_member)

        def depth(member_id: str) -> int:
            current = member_id
            seen: set[str] = set()
            levels = 0

            while current in manager_lookup:
                if current in seen:
                    raise ValueError(
                        "cyclic organizational reporting relationship detected"
                    )

                seen.add(current)
                current = manager_lookup[current]
                levels += 1

            return levels

        hierarchy_depth = max(
            (depth(member_id) for member_id in member_ids),
            default=0,
        )

        return OrganizationalCapacityResult(
            organization_id=organization_id,
            total_members=total_members,
            manager_count=manager_count,
            managed_member_count=managed_member_count,
            unmanaged_member_count=unmanaged_member_count,
            average_span_of_control=average_span,
            minimum_span_of_control=minimum_span,
            maximum_span_of_control=maximum_span,
            spans_by_manager=spans,
            unmanaged_members=unmanaged_members,
            hierarchy_depth=hierarchy_depth,
            overloaded_managers=overloaded_managers,
            capacity_threshold=capacity_threshold,
            read_only=True,
            executable=False,
            metadata={
                "source": "M36.3",
                "analytics_only": True,
                "read_only": True,
                "executable": False,
                "estimated_capacity_only": True,
            },
        )
