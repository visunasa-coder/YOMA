from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.action_planning import (
    ActionPlan,
    ActionPlanStep,
)
from yoma.office.control_orchestration import (
    ControlOrchestrationEngine,
)
from yoma.office.multi_action_execution import (
    MultiActionExecutionPlanEngine,
)
from yoma.office.execution_scheduling import (
    ExecutionSchedulingEngine,
)


def make_plan():
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
        ActionPlanStep(
            step_id="ASTEP-2",
            sequence=2,
            action_type="ticket.create",
            description="Create ticket",
            target_system_id="SYS-1",
            parameters={"priority": "high"},
            requires_human_approval=True,
        ),
    )

    plan = ActionPlan(
        plan_id="APLAN-TEST",
        decision_id="DINT-TEST",
        created_at=created,
        decision_type="operational_control",
        priority="high",
        reason="Test controlled execution scheduling",
        steps=steps,
        requires_human_approval=True,
    )

    orchestration = ControlOrchestrationEngine().build(plan)

    return MultiActionExecutionPlanEngine().build(orchestration)


def make_dependent_plan():
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
        ActionPlanStep(
            step_id="ASTEP-2",
            sequence=2,
            action_type="ticket.create",
            description="Create ticket",
            target_system_id="SYS-1",
            parameters={"priority": "high"},
            requires_human_approval=True,
        ),
    )

    plan = ActionPlan(
        plan_id="APLAN-DEPENDENT",
        decision_id="DINT-DEPENDENT",
        created_at=created,
        decision_type="operational_control",
        priority="high",
        reason="Test dependency-aware scheduling",
        steps=steps,
        requires_human_approval=True,
    )

    orchestration = ControlOrchestrationEngine().build(plan)
    execution_plan = MultiActionExecutionPlanEngine().build(orchestration)

    # M33.2 creates the MultiAction objects from orchestration steps.
    # Inject an explicit dependency into the second action for this
    # focused dependency-ordering test.
    actions = execution_plan.actions

    first = actions[0]
    second = actions[1]

    from yoma.office.multi_action_execution import MultiAction

    dependent_second = MultiAction(
        action_id=second.action_id,
        sequence=second.sequence,
        action_type=second.action_type,
        description=second.description,
        target_user_id=second.target_user_id,
        target_system_id=second.target_system_id,
        dependency_ids=(first.action_id,),
        parameters=second.parameters,
        requires_human_approval=True,
        executable=False,
    )

    return type(execution_plan)(
        execution_plan_id=execution_plan.execution_plan_id,
        orchestration_id=execution_plan.orchestration_id,
        plan_id=execution_plan.plan_id,
        decision_id=execution_plan.decision_id,
        created_at=execution_plan.created_at,
        actions=(first, dependent_second),
        requires_human_approval=True,
        executable=False,
        metadata=execution_plan.metadata,
    )


def test_schedule_builds_from_execution_plan():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
    scheduled = datetime(2026, 9, 6, 11, 0, tzinfo=timezone.utc)

    result = engine.schedule(
        plan,
        scheduled_at=scheduled,
        created_at=created,
    )

    assert result.schedule.status == "scheduled"
    assert result.action_count == 2
    assert result.schedule.execution_plan_id == plan.execution_plan_id


def test_schedule_preserves_dependency_order():
    plan = make_dependent_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
    scheduled = created + timedelta(hours=1)

    result = engine.schedule(
        plan,
        scheduled_at=scheduled,
        created_at=created,
    )

    assert result.execution_order.ordered_action_ids == (
        "MACT-APLAN-DEPENDENT-1",
        "MACT-APLAN-DEPENDENT-2",
    )

    assert result.schedule.ordered_action_ids == (
        "MACT-APLAN-DEPENDENT-1",
        "MACT-APLAN-DEPENDENT-2",
    )


def test_schedule_preserves_dependency_levels():
    plan = make_dependent_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    result = engine.schedule(
        plan,
        scheduled_at=created + timedelta(hours=1),
        created_at=created,
    )

    assert result.schedule.dependency_levels == (
        ("MACT-APLAN-DEPENDENT-1",),
        ("MACT-APLAN-DEPENDENT-2",),
    )


def test_schedule_contains_transaction_intelligence():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    result = engine.schedule(
        plan,
        scheduled_at=created + timedelta(hours=1),
        created_at=created,
    )

    assert result.transaction.transaction_id.startswith("TX-")
    assert result.schedule.transaction_id == result.transaction.transaction_id
    assert (
        result.schedule.transaction_boundary_id
        == result.transaction.boundary.boundary_id
    )


def test_schedule_requires_future_or_equal_time():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        engine.schedule(
            plan,
            scheduled_at=created - timedelta(seconds=1),
            created_at=created,
        )


def test_schedule_requires_timezone_aware_times():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    naive = datetime(2026, 9, 6, 10, 0)

    with pytest.raises(ValueError):
        engine.schedule(
            plan,
            scheduled_at=naive,
            created_at=naive,
        )


def test_ready_transition_only_after_scheduled_time():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
    scheduled = created + timedelta(hours=1)

    result = engine.schedule(
        plan,
        scheduled_at=scheduled,
        created_at=created,
    )

    before = engine.ready(
        result.schedule_id,
        now=scheduled - timedelta(seconds=1),
    )

    assert before.status == "scheduled"

    after = engine.ready(
        result.schedule_id,
        now=scheduled,
    )

    assert after.status == "ready"


def test_cancel_prevents_completion():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    result = engine.schedule(
        plan,
        scheduled_at=created + timedelta(hours=1),
        created_at=created,
    )

    cancelled = engine.cancel(result.schedule_id)

    assert cancelled.status == "cancelled"

    with pytest.raises(ValueError):
        engine.complete(result.schedule_id)


def test_ready_schedule_can_be_completed():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
    scheduled = created + timedelta(hours=1)

    result = engine.schedule(
        plan,
        scheduled_at=scheduled,
        created_at=created,
    )

    engine.ready(
        result.schedule_id,
        now=scheduled,
    )

    completed = engine.complete(result.schedule_id)

    assert completed.status == "completed"
    assert completed.executable is False
    assert completed.requires_human_approval is True


def test_scheduler_never_becomes_executable():
    plan = make_plan()
    engine = ExecutionSchedulingEngine()

    created = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)

    result = engine.schedule(
        plan,
        scheduled_at=created + timedelta(hours=1),
        created_at=created,
    )

    assert result.executable is False
    assert result.requires_human_approval is True
    assert result.schedule.executable is False
    assert result.schedule.requires_human_approval is True
    assert result.schedule.requires_review is True
