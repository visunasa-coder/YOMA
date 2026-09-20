from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Tuple

from yoma.office.multi_action_execution import (
    MultiAction,
    MultiActionExecutionPlan,
)


@dataclass(frozen=True)
class ExecutionOrder:
    order_id: str
    execution_plan_id: str
    ordered_action_ids: Tuple[str, ...] = ()
    dependency_levels: Tuple[Tuple[str, ...], ...] = ()
    blocked_action_ids: Tuple[str, ...] = ()
    missing_dependency_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.order_id.startswith("ORDER-"):
            raise ValueError("order_id must start with ORDER-")
        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")
        if not self.requires_human_approval:
            raise ValueError("execution ordering requires human approval")
        if self.executable:
            raise ValueError("execution ordering is not executable")

        flattened = tuple(
            action_id
            for level in self.dependency_levels
            for action_id in level
        )

        if flattened != self.ordered_action_ids:
            raise ValueError(
                "dependency levels must match ordered_action_ids"
            )


@dataclass(frozen=True)
class DependencyExecutionAnalysis:
    analysis_id: str
    execution_plan_id: str
    ready_action_ids: Tuple[str, ...] = ()
    blocked_action_ids: Tuple[str, ...] = ()
    missing_dependency_ids: Tuple[str, ...] = ()
    circular_dependency: bool = False
    dependency_count: int = 0
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.analysis_id.startswith("DEPAN-"):
            raise ValueError("analysis_id must start with DEPAN-")
        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")
        if not self.requires_human_approval:
            raise ValueError("dependency analysis requires human approval")
        if self.executable:
            raise ValueError("dependency analysis is not executable")

    @property
    def requires_review(self) -> bool:
        return bool(
            self.blocked_action_ids
            or self.missing_dependency_ids
            or self.circular_dependency
        )


class DependencyAwareExecutionEngine:
    """
    Determines a deterministic dependency-aware execution order.

    This engine performs planning/analysis only.
    It never invokes an executor.
    """

    def __init__(self) -> None:
        self._orders: dict[str, ExecutionOrder] = {}
        self._analyses: dict[str, DependencyExecutionAnalysis] = {}

    @property
    def orders(self) -> Tuple[ExecutionOrder, ...]:
        return tuple(self._orders.values())

    @property
    def analyses(self) -> Tuple[DependencyExecutionAnalysis, ...]:
        return tuple(self._analyses.values())

    def order(
        self,
        execution_plan: MultiActionExecutionPlan,
    ) -> ExecutionOrder:
        if not isinstance(
            execution_plan,
            MultiActionExecutionPlan,
        ):
            raise TypeError(
                "execution_plan must be a MultiActionExecutionPlan"
            )

        order_id = f"ORDER-{execution_plan.execution_plan_id}"

        existing = self._orders.get(order_id)
        if existing is not None:
            return existing

        actions = tuple(execution_plan.actions)
        action_lookup = {
            action.action_id: action
            for action in actions
        }

        if len(action_lookup) != len(actions):
            raise ValueError("execution plan contains duplicate action IDs")

        missing = set()

        for action in actions:
            for dependency_id in action.dependency_ids:
                if dependency_id not in action_lookup:
                    missing.add(dependency_id)

        if missing:
            missing_tuple = tuple(sorted(missing))

            result = ExecutionOrder(
                order_id=order_id,
                execution_plan_id=execution_plan.execution_plan_id,
                ordered_action_ids=(),
                dependency_levels=(),
                blocked_action_ids=tuple(
                    sorted(action.action_id for action in actions)
                ),
                missing_dependency_ids=missing_tuple,
                requires_human_approval=True,
                executable=False,
            )

            self._orders[order_id] = result
            return result

        dependencies = {
            action.action_id: set(action.dependency_ids)
            for action in actions
        }

        remaining = set(action_lookup)
        completed = set()
        levels = []

        while remaining:
            ready = sorted(
                action_id
                for action_id in remaining
                if dependencies[action_id].issubset(completed)
            )

            if not ready:
                raise ValueError(
                    "circular dependency detected in execution plan"
                )

            level = tuple(ready)
            levels.append(level)

            completed.update(ready)
            remaining.difference_update(ready)

        ordered = tuple(
            action_id
            for level in levels
            for action_id in level
        )

        result = ExecutionOrder(
            order_id=order_id,
            execution_plan_id=execution_plan.execution_plan_id,
            ordered_action_ids=ordered,
            dependency_levels=tuple(levels),
            blocked_action_ids=(),
            missing_dependency_ids=(),
            requires_human_approval=True,
            executable=False,
        )

        self._orders[order_id] = result
        return result

    def analyze(
        self,
        execution_plan: MultiActionExecutionPlan,
    ) -> DependencyExecutionAnalysis:
        if not isinstance(
            execution_plan,
            MultiActionExecutionPlan,
        ):
            raise TypeError(
                "execution_plan must be a MultiActionExecutionPlan"
            )

        analysis_id = f"DEPAN-{execution_plan.execution_plan_id}"

        existing = self._analyses.get(analysis_id)
        if existing is not None:
            return existing

        actions = tuple(execution_plan.actions)
        action_lookup = {
            action.action_id: action
            for action in actions
        }

        missing = {
            dependency_id
            for action in actions
            for dependency_id in action.dependency_ids
            if dependency_id not in action_lookup
        }

        if missing:
            result = DependencyExecutionAnalysis(
                analysis_id=analysis_id,
                execution_plan_id=execution_plan.execution_plan_id,
                ready_action_ids=(),
                blocked_action_ids=tuple(
                    sorted(action.action_id for action in actions)
                ),
                missing_dependency_ids=tuple(sorted(missing)),
                circular_dependency=False,
                dependency_count=sum(
                    len(action.dependency_ids)
                    for action in actions
                ),
                requires_human_approval=True,
                executable=False,
            )

            self._analyses[analysis_id] = result
            return result

        dependencies = {
            action.action_id: set(action.dependency_ids)
            for action in actions
        }

        ready = tuple(
            sorted(
                action_id
                for action_id, dependency_ids in dependencies.items()
                if not dependency_ids
            )
        )

        remaining = set(action_lookup)
        completed = set()

        while remaining:
            available = {
                action_id
                for action_id in remaining
                if dependencies[action_id].issubset(completed)
            }

            if not available:
                result = DependencyExecutionAnalysis(
                    analysis_id=analysis_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    ready_action_ids=ready,
                    blocked_action_ids=tuple(sorted(remaining)),
                    missing_dependency_ids=(),
                    circular_dependency=True,
                    dependency_count=sum(
                        len(action.dependency_ids)
                        for action in actions
                    ),
                    requires_human_approval=True,
                    executable=False,
                )

                self._analyses[analysis_id] = result
                return result

            completed.update(available)
            remaining.difference_update(available)

        result = DependencyExecutionAnalysis(
            analysis_id=analysis_id,
            execution_plan_id=execution_plan.execution_plan_id,
            ready_action_ids=ready,
            blocked_action_ids=(),
            missing_dependency_ids=(),
            circular_dependency=False,
            dependency_count=sum(
                len(action.dependency_ids)
                for action in actions
            ),
            requires_human_approval=True,
            executable=False,
        )

        self._analyses[analysis_id] = result
        return result

    def order_many(
        self,
        execution_plans: Iterable[MultiActionExecutionPlan],
    ) -> Tuple[ExecutionOrder, ...]:
        return tuple(
            self.order(execution_plan)
            for execution_plan in execution_plans
        )
