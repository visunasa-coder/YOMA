from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Tuple

from yoma.office.dependency_aware_execution import (
    DependencyAwareExecutionEngine,
    ExecutionOrder,
)
from yoma.office.multi_action_execution import MultiActionExecutionPlan
from yoma.office.transaction_rollback import (
    TransactionIntelligence,
    TransactionRollbackIntelligenceEngine,
)


VALID_SCHEDULE_STATUSES = {
    "scheduled",
    "ready",
    "cancelled",
    "completed",
}


@dataclass(frozen=True)
class ExecutionSchedule:
    schedule_id: str
    execution_plan_id: str
    orchestration_id: str
    decision_id: str
    scheduled_at: datetime
    created_at: datetime
    status: str = "scheduled"
    ordered_action_ids: Tuple[str, ...] = ()
    dependency_levels: Tuple[Tuple[str, ...], ...] = ()
    transaction_id: Optional[str] = None
    transaction_boundary_id: Optional[str] = None
    rollback_plan_id: Optional[str] = None
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.schedule_id.startswith("SCHED-"):
            raise ValueError("schedule_id must start with SCHED-")

        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")

        if not self.orchestration_id:
            raise ValueError("orchestration_id is required")

        if not self.decision_id:
            raise ValueError("decision_id is required")

        if self.scheduled_at.tzinfo is None or self.created_at.tzinfo is None:
            raise ValueError("scheduled_at and created_at must be timezone-aware")

        if self.status not in VALID_SCHEDULE_STATUSES:
            raise ValueError(f"invalid schedule status: {self.status}")

        if len(set(self.ordered_action_ids)) != len(self.ordered_action_ids):
            raise ValueError("ordered_action_ids must be unique")

        flattened = tuple(
            action_id
            for level in self.dependency_levels
            for action_id in level
        )

        if flattened != self.ordered_action_ids:
            raise ValueError(
                "dependency_levels must flatten to ordered_action_ids"
            )

        if not self.requires_human_approval:
            raise ValueError("execution scheduling always requires human approval")

        if self.executable:
            raise ValueError("execution scheduling is never executable")

    @property
    def action_count(self) -> int:
        return len(self.ordered_action_ids)

    @property
    def is_scheduled(self) -> bool:
        return self.status == "scheduled"

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval and not self.executable


@dataclass(frozen=True)
class ExecutionSchedulingResult:
    schedule: ExecutionSchedule
    execution_order: ExecutionOrder
    transaction: TransactionIntelligence
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.requires_human_approval:
            raise ValueError("scheduling result requires human approval")

        if self.executable:
            raise ValueError("scheduling result is never executable")

    @property
    def schedule_id(self) -> str:
        return self.schedule.schedule_id

    @property
    def action_count(self) -> int:
        return self.schedule.action_count

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval and not self.executable


class ExecutionSchedulingEngine:
    """
    M33.5 execution scheduling.

    This layer coordinates scheduling state only.
    It does NOT execute actions and does NOT bypass M32 approval.
    """

    def __init__(
        self,
        dependency_engine: Optional[DependencyAwareExecutionEngine] = None,
        transaction_engine: Optional[TransactionRollbackIntelligenceEngine] = None,
    ) -> None:
        self._dependency_engine = (
            dependency_engine or DependencyAwareExecutionEngine()
        )
        self._transaction_engine = (
            transaction_engine or TransactionRollbackIntelligenceEngine()
        )
        self._schedules: dict[str, ExecutionSchedule] = {}

    @staticmethod
    def _schedule_id(
        execution_plan: MultiActionExecutionPlan,
        scheduled_at: datetime,
    ) -> str:
        timestamp = scheduled_at.strftime("%Y%m%d%H%M%S%f")
        return f"SCHED-{execution_plan.execution_plan_id}-{timestamp}"

    def schedule(
        self,
        execution_plan: MultiActionExecutionPlan,
        *,
        scheduled_at: datetime,
        created_at: datetime,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionSchedulingResult:
        if not isinstance(execution_plan, MultiActionExecutionPlan):
            raise TypeError("execution_plan must be MultiActionExecutionPlan")

        if scheduled_at.tzinfo is None or created_at.tzinfo is None:
            raise ValueError("scheduled_at and created_at must be timezone-aware")

        if scheduled_at < created_at:
            raise ValueError("scheduled_at cannot be earlier than created_at")

        execution_order = self._dependency_engine.order(execution_plan)

        if execution_order.blocked_action_ids:
            raise ValueError(
                "cannot schedule a plan with blocked actions"
            )

        if execution_order.missing_dependency_ids:
            raise ValueError(
                "cannot schedule a plan with missing dependencies"
            )

        transaction = self._transaction_engine.build(
            execution_plan,
            execution_order,
        )

        schedule_id = self._schedule_id(
            execution_plan,
            scheduled_at,
        )

        if schedule_id in self._schedules:
            return ExecutionSchedulingResult(
                schedule=self._schedules[schedule_id],
                execution_order=execution_order,
                transaction=transaction,
            )

        schedule = ExecutionSchedule(
            schedule_id=schedule_id,
            execution_plan_id=execution_plan.execution_plan_id,
            orchestration_id=execution_plan.orchestration_id,
            decision_id=execution_plan.decision_id,
            scheduled_at=scheduled_at,
            created_at=created_at,
            status="scheduled",
            ordered_action_ids=execution_order.ordered_action_ids,
            dependency_levels=execution_order.dependency_levels,
            transaction_id=transaction.transaction_id,
            transaction_boundary_id=transaction.boundary.boundary_id,
            rollback_plan_id=transaction.rollback_plan.rollback_plan_id,
            requires_human_approval=True,
            executable=False,
            metadata=dict(metadata or {}),
        )

        self._schedules[schedule_id] = schedule

        return ExecutionSchedulingResult(
            schedule=schedule,
            execution_order=execution_order,
            transaction=transaction,
        )

    def schedule_many(
        self,
        execution_plans: Iterable[MultiActionExecutionPlan],
        *,
        scheduled_at: datetime,
        created_at: datetime,
    ) -> Tuple[ExecutionSchedulingResult, ...]:
        return tuple(
            self.schedule(
                plan,
                scheduled_at=scheduled_at,
                created_at=created_at,
            )
            for plan in execution_plans
        )

    def get(self, schedule_id: str) -> ExecutionSchedule:
        try:
            return self._schedules[schedule_id]
        except KeyError as exc:
            raise KeyError(f"unknown schedule: {schedule_id}") from exc

    @property
    def schedules(self) -> Tuple[ExecutionSchedule, ...]:
        return tuple(
            self._schedules[key]
            for key in sorted(self._schedules)
        )

    def ready(
        self,
        schedule_id: str,
        *,
        now: datetime,
    ) -> ExecutionSchedule:
        schedule = self.get(schedule_id)

        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        if schedule.status != "scheduled":
            return schedule

        if now < schedule.scheduled_at:
            return schedule

        updated = ExecutionSchedule(
            schedule_id=schedule.schedule_id,
            execution_plan_id=schedule.execution_plan_id,
            orchestration_id=schedule.orchestration_id,
            decision_id=schedule.decision_id,
            scheduled_at=schedule.scheduled_at,
            created_at=schedule.created_at,
            status="ready",
            ordered_action_ids=schedule.ordered_action_ids,
            dependency_levels=schedule.dependency_levels,
            transaction_id=schedule.transaction_id,
            transaction_boundary_id=schedule.transaction_boundary_id,
            rollback_plan_id=schedule.rollback_plan_id,
            requires_human_approval=True,
            executable=False,
            metadata=dict(schedule.metadata),
        )

        self._schedules[schedule_id] = updated
        return updated

    def cancel(self, schedule_id: str) -> ExecutionSchedule:
        schedule = self.get(schedule_id)

        if schedule.status in {"completed", "cancelled"}:
            return schedule

        updated = ExecutionSchedule(
            schedule_id=schedule.schedule_id,
            execution_plan_id=schedule.execution_plan_id,
            orchestration_id=schedule.orchestration_id,
            decision_id=schedule.decision_id,
            scheduled_at=schedule.scheduled_at,
            created_at=schedule.created_at,
            status="cancelled",
            ordered_action_ids=schedule.ordered_action_ids,
            dependency_levels=schedule.dependency_levels,
            transaction_id=schedule.transaction_id,
            transaction_boundary_id=schedule.transaction_boundary_id,
            rollback_plan_id=schedule.rollback_plan_id,
            requires_human_approval=True,
            executable=False,
            metadata=dict(schedule.metadata),
        )

        self._schedules[schedule_id] = updated
        return updated

    def complete(self, schedule_id: str) -> ExecutionSchedule:
        schedule = self.get(schedule_id)

        if schedule.status != "ready":
            raise ValueError(
                "only a ready schedule can be marked completed"
            )

        updated = ExecutionSchedule(
            schedule_id=schedule.schedule_id,
            execution_plan_id=schedule.execution_plan_id,
            orchestration_id=schedule.orchestration_id,
            decision_id=schedule.decision_id,
            scheduled_at=schedule.scheduled_at,
            created_at=schedule.created_at,
            status="completed",
            ordered_action_ids=schedule.ordered_action_ids,
            dependency_levels=schedule.dependency_levels,
            transaction_id=schedule.transaction_id,
            transaction_boundary_id=schedule.transaction_boundary_id,
            rollback_plan_id=schedule.rollback_plan_id,
            requires_human_approval=True,
            executable=False,
            metadata=dict(schedule.metadata),
        )

        self._schedules[schedule_id] = updated
        return updated

    def clear(self) -> None:
        self._schedules.clear()
