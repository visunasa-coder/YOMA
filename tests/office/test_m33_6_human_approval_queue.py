from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.action_planning import ActionPlan, ActionPlanStep
from yoma.office.control_orchestration import ControlOrchestrationEngine
from yoma.office.multi_action_execution import MultiActionExecutionPlanEngine
from yoma.office.execution_scheduling import ExecutionSchedulingEngine
from yoma.office.human_approval_queue import HumanApprovalQueueEngine


def make_plan(
    plan_id="APLAN-QUEUE",
    decision_id="DINT-QUEUE",
    priority="high",
):
    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    steps = (
        ActionPlanStep(
            step_id="ASTEP-1",
            sequence=1,
            action_type="email.send",
            description="Send notification",
            target_user_id="USER-1",
            parameters={"message": "hello"},
            requires_human_approval=True,
        ),
    )

    return ActionPlan(
        plan_id=plan_id,
        decision_id=decision_id,
        created_at=created,
        decision_type="operational_control",
        priority=priority,
        reason="Human approval queue test",
        steps=steps,
        requires_human_approval=True,
    )


def make_schedule(plan):
    orchestration = ControlOrchestrationEngine().build(plan)
    execution_plan = MultiActionExecutionPlanEngine().build(orchestration)

    created = plan.created_at

    return ExecutionSchedulingEngine().schedule(
        execution_plan,
        scheduled_at=created + timedelta(hours=1),
        created_at=created,
    ).schedule


def test_enqueue_creates_pending_item():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    assert item.status == "pending"
    assert item.requires_review is True
    assert item.executable is False


def test_enqueue_preserves_plan_and_schedule_identity():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    assert item.schedule_id == schedule.schedule_id
    assert item.execution_plan_id == schedule.execution_plan_id
    assert item.plan_id == plan.plan_id
    assert item.decision_id == plan.decision_id


def test_duplicate_enqueue_is_idempotent():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()

    first = queue.enqueue(schedule, plan)
    second = queue.enqueue(schedule, plan)

    assert first == second
    assert len(queue.items) == 1


def test_pending_queue_contains_item():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    assert queue.pending == (item,)
    assert queue.approved == ()


def test_approve_uses_existing_approval_engine():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    approved = queue.approve(
        item.queue_item_id,
        "REVIEWER-1",
        datetime(2026, 9, 6, 10, 30, tzinfo=timezone.utc),
        "Approved for controlled execution",
    )

    assert approved.status == "approved"
    assert approved.workflow.status == "approved"
    assert approved.workflow.approval_history
    assert approved.workflow.approval_history[-1].reviewer_id == "REVIEWER-1"


def test_reject_uses_existing_approval_engine():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    rejected = queue.reject(
        item.queue_item_id,
        "REVIEWER-2",
        datetime(2026, 9, 6, 10, 30, tzinfo=timezone.utc),
        "Rejected pending clarification",
    )

    assert rejected.status == "rejected"
    assert rejected.workflow.status == "rejected"


def test_modify_uses_existing_approval_engine():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    modified = queue.modify(
        item.queue_item_id,
        "REVIEWER-3",
        datetime(2026, 9, 6, 10, 30, tzinfo=timezone.utc),
        {"priority": "normal"},
        "Modified priority",
    )

    assert modified.status == "modified"
    assert modified.workflow.status == "modified"
    assert modified.workflow.approval_history[-1].modifications["priority"] == "normal"


def test_prioritized_pending_orders_by_priority():
    plans = (
        make_plan("APLAN-LOW", "DINT-LOW", "low"),
        make_plan("APLAN-CRITICAL", "DINT-CRITICAL", "critical"),
        make_plan("APLAN-HIGH", "DINT-HIGH", "high"),
    )

    queue = HumanApprovalQueueEngine()

    for plan in plans:
        queue.enqueue(make_schedule(plan), plan)

    ordered = queue.prioritized_pending()

    assert [item.priority for item in ordered] == [
        "critical",
        "high",
        "low",
    ]


def test_approval_requires_human_reviewer():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    with pytest.raises(ValueError):
        queue.approve(
            item.queue_item_id,
            "",
            datetime(2026, 9, 6, 10, 30, tzinfo=timezone.utc),
        )


def test_queue_never_becomes_executable():
    plan = make_plan()
    schedule = make_schedule(plan)

    queue = HumanApprovalQueueEngine()
    item = queue.enqueue(schedule, plan)

    approved = queue.approve(
        item.queue_item_id,
        "REVIEWER-4",
        datetime(2026, 9, 6, 10, 30, tzinfo=timezone.utc),
    )

    assert item.executable is False
    assert approved.executable is False
    assert approved.requires_human_approval is True
