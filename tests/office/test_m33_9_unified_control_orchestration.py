from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.action_planning import ActionPlan, ActionPlanStep
from yoma.office.unified_control_orchestration import (
    UnifiedControlOrchestrationResult,
    UnifiedControlOrchestrationRuntime,
)


def make_plan():
    now = datetime.now(timezone.utc)

    step1 = ActionPlanStep(
        step_id="STEP-UNIFIED-1",
        sequence=1,
        action_type="gmail",
        description="Prepare Gmail action",
        target_system_id="gmail",
    )

    step2 = ActionPlanStep(
        step_id="STEP-UNIFIED-2",
        sequence=2,
        action_type="slack",
        description="Prepare Slack action",
        target_system_id="slack",
    )

    return ActionPlan(
        plan_id="APLAN-UNIFIED-001",
        decision_id="DINT-UNIFIED-001",
        created_at=now,
        decision_type="operational_control",
        priority="high",
        reason="Unified orchestration test",
        steps=(step1, step2),
        affected_system_ids=("gmail", "slack"),
    )


def run_runtime():
    runtime = UnifiedControlOrchestrationRuntime()
    now = datetime.now(timezone.utc)

    return runtime.orchestrate(
        make_plan(),
        scheduled_at=now + timedelta(hours=1),
        created_at=now,
    )


def test_unified_runtime_composes_all_m33_layers():
    result = run_runtime()

    assert isinstance(result, UnifiedControlOrchestrationResult)
    assert result.orchestration.orchestration_id.startswith("ORCH-")
    assert result.execution_plan.execution_plan_id.startswith("MAPLAN-")
    assert result.execution_order.order_id.startswith("ORDER-")
    assert result.transaction.transaction_id.startswith("TX-")
    assert result.schedule.schedule_id.startswith("SCHED-")
    assert result.coordination.coordination_id.startswith("XCOORD-")
    assert result.intelligence.intelligence_id.startswith("OINT-")


def test_all_actions_are_preserved():
    result = run_runtime()

    assert result.action_count == 2
    assert tuple(
        action.action_type
        for action in result.execution_plan.actions
    ) == ("gmail", "slack")


def test_dependency_order_is_present():
    result = run_runtime()

    assert len(result.execution_order.ordered_action_ids) == 2
    assert (
        result.execution_order.ordered_action_ids[0]
        != result.execution_order.ordered_action_ids[1]
    )


def test_dependency_analysis_is_present():
    result = run_runtime()

    assert (
        result.dependency_analysis.execution_plan_id
        == result.execution_plan.execution_plan_id
    )
    assert result.dependency_analysis.dependency_count >= 0


def test_transaction_is_present():
    result = run_runtime()

    assert (
        result.transaction.execution_plan_id
        == result.execution_plan.execution_plan_id
    )
    assert len(result.transaction.boundary.action_ids) == 2


def test_schedule_is_connected():
    result = run_runtime()

    assert (
        result.schedule.execution_plan_id
        == result.execution_plan.execution_plan_id
    )
    assert (
        result.schedule.ordered_action_ids
        == result.execution_order.ordered_action_ids
    )


def test_human_approval_queue_is_created():
    result = run_runtime()

    assert len(result.approval_items) == 1

    item = result.approval_items[0]

    assert item.schedule_id == result.schedule.schedule_id
    assert (
        item.execution_plan_id
        == result.execution_plan.execution_plan_id
    )
    assert item.status == "pending"
    assert item.requires_human_approval is True
    assert item.executable is False


def test_cross_system_coordination_is_present():
    result = run_runtime()

    assert result.system_count == 2
    assert set(
        result.coordination.participating_system_ids
    ) == {"gmail", "slack"}


def test_orchestration_intelligence_is_present():
    result = run_runtime()

    assert (
        result.intelligence.orchestration_id
        == result.orchestration.orchestration_id
    )
    assert (
        result.intelligence.execution_plan_id
        == result.execution_plan.execution_plan_id
    )


def test_unified_runtime_never_executes():
    result = run_runtime()

    assert result.requires_human_approval is True
    assert result.executable is False
    assert result.orchestration.executable is False
    assert result.execution_plan.executable is False
    assert result.execution_order.executable is False
    assert result.transaction.executable is False
    assert result.schedule.executable is False
    assert result.coordination.executable is False
    assert result.intelligence.executable is False


def test_runtime_is_cached_deterministically():
    runtime = UnifiedControlOrchestrationRuntime()
    now = datetime.now(timezone.utc)
    plan = make_plan()

    first = runtime.orchestrate(
        plan,
        scheduled_at=now + timedelta(hours=1),
        created_at=now,
    )

    second = runtime.orchestrate(
        plan,
        scheduled_at=now + timedelta(hours=1),
        created_at=now,
    )

    assert first is second
    assert runtime.get(first.execution_plan_id) is first
    assert len(runtime.results) == 1


def test_runtime_rejects_naive_schedule_timestamp():
    runtime = UnifiedControlOrchestrationRuntime()
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.orchestrate(
            make_plan(),
            scheduled_at=datetime.now(),
            created_at=now,
        )
