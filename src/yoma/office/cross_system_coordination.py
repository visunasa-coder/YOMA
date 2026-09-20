from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple


def _require_id(value: str, prefix: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if not value.startswith(prefix):
        raise ValueError(f"{name} must start with {prefix}")


def _unique(values: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True)
class SystemActionGroup:
    group_id: str
    system_id: str
    execution_plan_id: str
    action_ids: Tuple[str, ...] = ()
    action_sequences: Tuple[int, ...] = ()
    dependency_system_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        _require_id(self.group_id, "SGRP-", "group_id")

        if not self.system_id:
            raise ValueError("system_id must be non-empty")

        if not self.execution_plan_id:
            raise ValueError("execution_plan_id must be non-empty")

        if len(self.action_ids) != len(set(self.action_ids)):
            raise ValueError("action_ids must be unique")

        if len(self.action_sequences) != len(self.action_ids):
            raise ValueError(
                "action_sequences must correspond to action_ids"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "cross-system coordination requires human approval"
            )

        if self.executable:
            raise ValueError(
                "cross-system coordination groups are non-executable"
            )

    @property
    def action_count(self) -> int:
        return len(self.action_ids)


@dataclass(frozen=True)
class SystemCoordinationOrder:
    order_id: str
    coordination_id: str
    ordered_system_ids: Tuple[str, ...] = ()
    dependency_levels: Tuple[Tuple[str, ...], ...] = ()
    blocked_system_ids: Tuple[str, ...] = ()
    missing_system_ids: Tuple[str, ...] = ()
    circular_dependency: bool = False
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        _require_id(self.order_id, "SYSORDER-", "order_id")
        _require_id(self.coordination_id, "XCOORD-", "coordination_id")

        if not self.requires_human_approval:
            raise ValueError(
                "system coordination ordering requires human approval"
            )

        if self.executable:
            raise ValueError(
                "system coordination ordering is non-executable"
            )

        flattened = tuple(
            system_id
            for level in self.dependency_levels
            for system_id in level
        )

        if flattened != self.ordered_system_ids:
            raise ValueError(
                "dependency_levels must flatten to ordered_system_ids"
            )

    @property
    def system_count(self) -> int:
        return len(self.ordered_system_ids)

    @property
    def requires_review(self) -> bool:
        return bool(
            self.blocked_system_ids
            or self.missing_system_ids
            or self.circular_dependency
        )


@dataclass(frozen=True)
class CrossSystemCoordination:
    coordination_id: str
    execution_plan_id: str
    orchestration_id: str
    plan_id: str
    decision_id: str
    created_at: datetime
    participating_system_ids: Tuple[str, ...] = ()
    groups: Tuple[SystemActionGroup, ...] = ()
    system_dependencies: Mapping[str, Tuple[str, ...]] = field(
        default_factory=dict
    )
    unresolved_system_ids: Tuple[str, ...] = ()
    coordination_order: Optional[SystemCoordinationOrder] = None
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_id(
            self.coordination_id,
            "XCOORD-",
            "coordination_id",
        )

        if not self.execution_plan_id:
            raise ValueError("execution_plan_id must be non-empty")

        if not self.orchestration_id:
            raise ValueError("orchestration_id must be non-empty")

        if not self.plan_id:
            raise ValueError("plan_id must be non-empty")

        if not self.decision_id:
            raise ValueError("decision_id must be non-empty")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        if len(self.participating_system_ids) != len(
            set(self.participating_system_ids)
        ):
            raise ValueError(
                "participating_system_ids must be unique"
            )

        group_systems = tuple(group.system_id for group in self.groups)

        if len(group_systems) != len(set(group_systems)):
            raise ValueError(
                "there must be at most one group per system"
            )

        if set(group_systems) != set(self.participating_system_ids):
            raise ValueError(
                "groups must match participating_system_ids"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "cross-system coordination requires human approval"
            )

        if self.executable:
            raise ValueError(
                "cross-system coordination is non-executable"
            )

        if self.coordination_order is not None:
            if (
                self.coordination_order.coordination_id
                != self.coordination_id
            ):
                raise ValueError(
                    "coordination order must match coordination"
                )

    @property
    def system_count(self) -> int:
        return len(self.participating_system_ids)

    @property
    def action_count(self) -> int:
        return sum(group.action_count for group in self.groups)

    @property
    def multi_system(self) -> bool:
        return self.system_count > 1

    @property
    def requires_review(self) -> bool:
        return bool(
            self.unresolved_system_ids
            or (
                self.coordination_order is not None
                and self.coordination_order.requires_review
            )
        )


class CrossSystemCoordinationEngine:
    """
    M33.7 Cross-System Control Coordination.

    This layer coordinates actions across systems but never executes
    them. It deliberately reuses MultiActionExecutionPlan and the
    existing integration metadata supplied by the caller.
    """

    def __init__(
        self,
        integrations: Tuple[Any, ...] = (),
    ) -> None:
        self._integrations = tuple(integrations)
        self._integrations_by_name = {
            integration.name: integration
            for integration in self._integrations
        }
        self._cache: dict[str, CrossSystemCoordination] = {}

    @property
    def integrations(self) -> Tuple[Any, ...]:
        return self._integrations

    def _available_system_ids(self) -> set[str]:
        return set(self._integrations_by_name)

    def _coordination_id(self, execution_plan: Any) -> str:
        action_ids = ",".join(
            action.action_id
            for action in execution_plan.actions
        )

        return (
            f"XCOORD-{execution_plan.execution_plan_id}-"
            f"{execution_plan.orchestration_id}-"
            f"{action_ids or 'EMPTY'}"
        )

    def _validate_plan(self, execution_plan: Any) -> None:
        if not execution_plan.execution_plan_id:
            raise ValueError("execution plan ID is required")

        if not execution_plan.orchestration_id:
            raise ValueError("orchestration ID is required")

        if not execution_plan.plan_id:
            raise ValueError("plan ID is required")

        if not execution_plan.decision_id:
            raise ValueError("decision ID is required")

        if not execution_plan.requires_human_approval:
            raise ValueError(
                "execution plan must require human approval"
            )

        if execution_plan.executable:
            raise ValueError(
                "execution plan must be non-executable"
            )

        for action in execution_plan.actions:
            if not action.requires_human_approval:
                raise ValueError(
                    "all coordinated actions require human approval"
                )
            if action.executable:
                raise ValueError(
                    "coordinated actions must be non-executable"
                )

    def _build_groups(
        self,
        execution_plan: Any,
    ) -> tuple[
        Tuple[str, ...],
        Tuple[SystemActionGroup, ...],
        Tuple[str, ...],
        dict[str, set[str]],
    ]:
        by_system: dict[str, list[Any]] = {}
        unresolved: set[str] = set()

        for action in execution_plan.actions:
            system_id = action.target_system_id

            if not system_id:
                unresolved.add("UNSPECIFIED")

                by_system.setdefault("UNSPECIFIED", []).append(action)
                continue

            by_system.setdefault(system_id, []).append(action)

            if (
                self._integrations
                and system_id not in self._available_system_ids()
            ):
                unresolved.add(system_id)

        participating = tuple(sorted(by_system))

        dependencies: dict[str, set[str]] = {
            system_id: set()
            for system_id in participating
        }

        for system_id, actions in by_system.items():
            for action in actions:
                for dependency_id in action.dependency_ids:
                    dependency_action = next(
                        (
                            candidate
                            for candidate in execution_plan.actions
                            if candidate.action_id == dependency_id
                        ),
                        None,
                    )

                    if dependency_action is None:
                        continue

                    dependency_system = (
                        dependency_action.target_system_id
                        or "UNSPECIFIED"
                    )

                    if dependency_system != system_id:
                        dependencies[system_id].add(
                            dependency_system
                        )

        groups: list[SystemActionGroup] = []

        for system_id in participating:
            actions = sorted(
                by_system[system_id],
                key=lambda action: (action.sequence, action.action_id),
            )

            groups.append(
                SystemActionGroup(
                    group_id=f"SGRP-{execution_plan.execution_plan_id}-{system_id}",
                    system_id=system_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    action_ids=tuple(
                        action.action_id for action in actions
                    ),
                    action_sequences=tuple(
                        action.sequence for action in actions
                    ),
                    dependency_system_ids=tuple(
                        sorted(dependencies[system_id])
                    ),
                )
            )

        return (
            participating,
            tuple(groups),
            tuple(sorted(unresolved)),
            dependencies,
        )

    def _order_systems(
        self,
        coordination_id: str,
        participating: Tuple[str, ...],
        dependencies: Mapping[str, set[str]],
        unresolved: Tuple[str, ...],
    ) -> SystemCoordinationOrder:
        unresolved_set = set(unresolved)

        if "UNSPECIFIED" in unresolved_set:
            unresolved_set.add("UNSPECIFIED")

        remaining = set(participating)
        ordered: list[str] = []
        levels: list[Tuple[str, ...]] = []
        blocked: set[str] = set(unresolved_set)

        while remaining:
            ready = sorted(
                system_id
                for system_id in remaining
                if all(
                    dependency in ordered
                    for dependency in dependencies.get(system_id, set())
                )
            )

            if not ready:
                raise ValueError(
                    "circular cross-system dependency detected"
                )

            level = tuple(ready)
            levels.append(level)

            for system_id in ready:
                ordered.append(system_id)
                remaining.remove(system_id)

        blocked -= set(ordered)

        return SystemCoordinationOrder(
            order_id=f"SYSORDER-{coordination_id}",
            coordination_id=coordination_id,
            ordered_system_ids=tuple(ordered),
            dependency_levels=tuple(levels),
            blocked_system_ids=tuple(sorted(blocked)),
            missing_system_ids=tuple(sorted(unresolved_set)),
        )

    def coordinate(
        self,
        execution_plan: Any,
    ) -> CrossSystemCoordination:
        self._validate_plan(execution_plan)

        coordination_id = self._coordination_id(execution_plan)

        if coordination_id in self._cache:
            return self._cache[coordination_id]

        (
            participating,
            groups,
            unresolved,
            dependencies,
        ) = self._build_groups(execution_plan)

        coordination_order = self._order_systems(
            coordination_id,
            participating,
            dependencies,
            unresolved,
        )

        coordination = CrossSystemCoordination(
            coordination_id=coordination_id,
            execution_plan_id=execution_plan.execution_plan_id,
            orchestration_id=execution_plan.orchestration_id,
            plan_id=execution_plan.plan_id,
            decision_id=execution_plan.decision_id,
            created_at=execution_plan.created_at,
            participating_system_ids=participating,
            groups=groups,
            system_dependencies={
                system_id: tuple(sorted(system_dependencies))
                for system_id, system_dependencies
                in sorted(dependencies.items())
            },
            unresolved_system_ids=unresolved,
            coordination_order=coordination_order,
        )

        self._cache[coordination_id] = coordination
        return coordination

    def coordinate_many(
        self,
        execution_plans: Tuple[Any, ...],
    ) -> Tuple[CrossSystemCoordination, ...]:
        return tuple(
            self.coordinate(execution_plan)
            for execution_plan in execution_plans
        )

    def get(self, coordination_id: str) -> CrossSystemCoordination:
        _require_id(
            coordination_id,
            "XCOORD-",
            "coordination_id",
        )

        try:
            return self._cache[coordination_id]
        except KeyError as exc:
            raise KeyError(
                f"unknown coordination: {coordination_id}"
            ) from exc

    @property
    def coordinations(self) -> Tuple[CrossSystemCoordination, ...]:
        return tuple(
            self._cache[key]
            for key in sorted(self._cache)
        )

    def clear(self) -> None:
        self._cache.clear()
