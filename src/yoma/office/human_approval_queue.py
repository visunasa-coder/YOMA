from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from yoma.office.action_planning import ActionPlan
from yoma.office.action_approval import (
    ActionApprovalEngine,
    ActionApprovalWorkflow,
)
from yoma.office.execution_scheduling import ExecutionSchedule


VALID_QUEUE_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "modified",
}


@dataclass(frozen=True)
class ApprovalQueueItem:
    queue_item_id: str
    schedule_id: str
    execution_plan_id: str
    plan_id: str
    decision_id: str
    priority: str
    scheduled_at: datetime
    created_at: datetime
    workflow: ActionApprovalWorkflow
    status: str = "pending"
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.queue_item_id.startswith("AQITEM-"):
            raise ValueError("queue_item_id must start with AQITEM-")

        if not self.schedule_id:
            raise ValueError("schedule_id is required")

        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")

        if not self.plan_id:
            raise ValueError("plan_id is required")

        if not self.decision_id:
            raise ValueError("decision_id is required")

        if self.status not in VALID_QUEUE_STATUSES:
            raise ValueError(f"invalid queue status: {self.status}")

        if self.scheduled_at.tzinfo is None or self.created_at.tzinfo is None:
            raise ValueError(
                "scheduled_at and created_at must be timezone-aware"
            )

        if self.workflow.plan_id != self.plan_id:
            raise ValueError("workflow plan_id does not match queue item")

        if self.workflow.decision_id != self.decision_id:
            raise ValueError("workflow decision_id does not match queue item")

        if self.workflow.status != self.status:
            raise ValueError(
                "queue status must match approval workflow status"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "approval queue always requires human approval"
            )

        if self.executable:
            raise ValueError(
                "approval queue is never executable"
            )

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def is_rejected(self) -> bool:
        return self.status == "rejected"

    @property
    def is_modified(self) -> bool:
        return self.status == "modified"

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval and self.status == "pending"


class HumanApprovalQueue:
    """
    M33.6 queue for human approval of scheduled execution plans.

    This class coordinates M31.6 approval workflows.
    It never executes actions.
    """

    def __init__(
        self,
        approval_engine: Optional[ActionApprovalEngine] = None,
    ) -> None:
        self._approval_engine = approval_engine or ActionApprovalEngine()
        self._items: dict[str, ApprovalQueueItem] = {}

    @staticmethod
    def _queue_item_id(schedule: ExecutionSchedule) -> str:
        return f"AQITEM-{schedule.schedule_id}"

    def enqueue(
        self,
        schedule: ExecutionSchedule,
        plan: ActionPlan,
    ) -> ApprovalQueueItem:
        if not isinstance(schedule, ExecutionSchedule):
            raise TypeError("schedule must be ExecutionSchedule")

        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be ActionPlan")

        if schedule.plan_id if hasattr(schedule, "plan_id") else False:
            if schedule.plan_id != plan.plan_id:
                raise ValueError("schedule and plan IDs do not match")

        if schedule.decision_id != plan.decision_id:
            raise ValueError("schedule and plan decision IDs do not match")

        if schedule.execution_plan_id == "":
            raise ValueError("execution_plan_id is required")

        item_id = self._queue_item_id(schedule)

        existing = self._items.get(item_id)
        if existing is not None:
            return existing

        workflow = self._approval_engine.create(plan)

        item = ApprovalQueueItem(
            queue_item_id=item_id,
            schedule_id=schedule.schedule_id,
            execution_plan_id=schedule.execution_plan_id,
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            priority=plan.priority,
            scheduled_at=schedule.scheduled_at,
            created_at=schedule.created_at,
            workflow=workflow,
            status=workflow.status,
            requires_human_approval=True,
            executable=False,
            metadata={
                "schedule_status": schedule.status,
                "action_count": schedule.action_count,
            },
        )

        self._items[item_id] = item
        return item

    def get(self, queue_item_id: str) -> ApprovalQueueItem:
        try:
            return self._items[queue_item_id]
        except KeyError as exc:
            raise KeyError(
                f"unknown approval queue item: {queue_item_id}"
            ) from exc

    @property
    def items(self) -> Tuple[ApprovalQueueItem, ...]:
        return tuple(
            self._items[key]
            for key in sorted(self._items)
        )

    @property
    def pending(self) -> Tuple[ApprovalQueueItem, ...]:
        return tuple(
            item
            for item in self.items
            if item.status == "pending"
        )

    @property
    def approved(self) -> Tuple[ApprovalQueueItem, ...]:
        return tuple(
            item
            for item in self.items
            if item.status == "approved"
        )

    def prioritized_pending(self) -> Tuple[ApprovalQueueItem, ...]:
        priority_rank = {
            "critical": 0,
            "high": 1,
            "normal": 2,
            "low": 3,
        }

        return tuple(
            sorted(
                self.pending,
                key=lambda item: (
                    priority_rank.get(item.priority, 99),
                    item.scheduled_at,
                    item.created_at,
                    item.queue_item_id,
                ),
            )
        )

    @staticmethod
    def _replace(
        item: ApprovalQueueItem,
        workflow: ActionApprovalWorkflow,
    ) -> ApprovalQueueItem:
        return ApprovalQueueItem(
            queue_item_id=item.queue_item_id,
            schedule_id=item.schedule_id,
            execution_plan_id=item.execution_plan_id,
            plan_id=item.plan_id,
            decision_id=item.decision_id,
            priority=item.priority,
            scheduled_at=item.scheduled_at,
            created_at=item.created_at,
            workflow=workflow,
            status=workflow.status,
            requires_human_approval=True,
            executable=False,
            metadata=dict(item.metadata),
        )

    def approve(
        self,
        queue_item_id: str,
        reviewer_id: str,
        decided_at: datetime,
        comment: str = "",
    ) -> ApprovalQueueItem:
        item = self.get(queue_item_id)

        workflow = self._approval_engine.approve(
            item.workflow,
            reviewer_id,
            decided_at,
            comment,
        )

        updated = self._replace(item, workflow)
        self._items[queue_item_id] = updated
        return updated

    def reject(
        self,
        queue_item_id: str,
        reviewer_id: str,
        decided_at: datetime,
        comment: str = "",
    ) -> ApprovalQueueItem:
        item = self.get(queue_item_id)

        workflow = self._approval_engine.reject(
            item.workflow,
            reviewer_id,
            decided_at,
            comment,
        )

        updated = self._replace(item, workflow)
        self._items[queue_item_id] = updated
        return updated

    def modify(
        self,
        queue_item_id: str,
        reviewer_id: str,
        decided_at: datetime,
        modifications: Mapping[str, Any],
        comment: str = "",
    ) -> ApprovalQueueItem:
        item = self.get(queue_item_id)

        workflow = self._approval_engine.modify(
            item.workflow,
            reviewer_id,
            decided_at,
            modifications,
            comment,
        )

        updated = self._replace(item, workflow)
        self._items[queue_item_id] = updated
        return updated

    def clear(self) -> None:
        self._items.clear()


class HumanApprovalQueueEngine(HumanApprovalQueue):
    """
    Named engine facade for M33.6.

    Inherits queue behavior while keeping approval lifecycle delegated
    to the existing M31.6 ActionApprovalEngine.
    """

    pass
