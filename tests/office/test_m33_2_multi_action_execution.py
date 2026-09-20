from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import ActionPlan, ActionPlanStep
from yoma.office.control_orchestration import ControlOrchestrationEngine
from yoma.office.multi_action_execution import (
    MultiAction,
    MultiActionExecutionPlan,
    MultiActionExecutionPlanEngine,
)


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_orchestration():
    plan = ActionPlan(
        plan_id="APLAN-M33-2",
        decision_id="DINT-M33-2",
        created_at=NOW,
        decision_type="workload_review",
        priority="high",
        reason="Coordinate multiple approved operational actions.",
        steps=(
            ActionPlanStep(
                step_id="ASTEP-M33-2-1",
                sequence=1,
                action_type="notify.manager",
                description="Notify manager.",
                target_user_id="EMP-001",
                parameters={"channel": "email"},
            ),
            ActionPlanStep(
                step_id="ASTEP-M33-2-2",
                sequence=2,
                action_type="review.workload",
                description="Review workload.",
                target_user_id="EMP-001",
            ),
            ActionPlanStep(
                step_id="ASTEP-M33-2-3",
                sequence=3,
                action_type="update.schedule",
                description="Update schedule.",
                target_user_id="EMP-001",
            ),
        ),
        affected_user_ids=("EMP-001",),
        affected_system_ids=("SYS-001",),
    )

    return ControlOrchestrationEngine().build(plan)


def test_build_multi_action_plan():
    orchestration = make_orchestration()
    engine = MultiActionExecutionPlanEngine()

    result = engine.build(orchestration)

    assert result.execution_plan_id == "MAPLAN-ORCH-APLAN-M33-2"
    assert result.orchestration_id == orchestration.orchestration_id
    assert result.plan_id == orchestration.plan_id
    assert result.decision_id == orchestration.decision_id


def test_all_actions_are_preserved():
    result = MultiActionExecutionPlanEngine().build(
        make_orchestration()
    )

    assert result.action_count == 3
    assert result.action_types == (
        "notify.manager",
        "review.workload",
        "update.schedule",
    )


def test_action_order_is_preserved():
    result = MultiActionExecutionPlanEngine().build(
        make_orchestration()
    )

    assert [action.sequence for action in result.actions] == [1, 2, 3]


def test_action_ids_are_deterministic():
    result = MultiActionExecutionPlanEngine().build(
        make_orchestration()
    )

    assert result.action_ids == (
        "MACT-APLAN-M33-2-1",
        "MACT-APLAN-M33-2-2",
        "MACT-APLAN-M33-2-3",
    )


def test_action_parameters_are_preserved():
    result = MultiActionExecutionPlanEngine().build(
        make_orchestration()
    )

    assert result.actions[0].parameters["channel"] == "email"


def test_human_approval_is_mandatory():
    result = MultiActionExecutionPlanEngine().build(
        make_orchestration()
    )

    assert result.requires_human_approval is True
    assert result.executable is False
    assert all(
        action.requires_human_approval
        for action in result.actions
    )
    assert all(
        not action.executable
        for action in result.actions
    )


def test_dependency_ids_are_preserved():
    orchestration = make_orchestration()

    modified_step = orchestration.steps[1]

    dependency = "DEP-M33-2"

    replacement = type(modified_step)(
        step_id=modified_step.step_id,
        sequence=modified_step.sequence,
        plan_id=modified_step.plan_id,
        action_type=modified_step.action_type,
        description=modified_step.description,
        target_user_id=modified_step.target_user_id,
        target_system_id=modified_step.target_system_id,
        dependency_ids=(dependency,),
        parameters=modified_step.parameters,
        requires_human_approval=True,
        executable=False,
    )

    modified = type(orchestration)(
        orchestration_id=orchestration.orchestration_id,
        plan_id=orchestration.plan_id,
        decision_id=orchestration.decision_id,
        created_at=orchestration.created_at,
        steps=(orchestration.steps[0], replacement, orchestration.steps[2]),
        dependency_map_id=orchestration.dependency_map_id,
        affected_user_ids=orchestration.affected_user_ids,
        affected_system_ids=orchestration.affected_system_ids,
        requires_human_approval=True,
        executable=False,
        metadata=orchestration.metadata,
    )

    result = MultiActionExecutionPlanEngine().build(modified)

    assert result.actions[1].dependency_ids == (dependency,)
    assert dependency in result.dependency_ids


def test_duplicate_action_ids_are_rejected():
    with pytest.raises(ValueError):
        MultiActionExecutionPlan(
            execution_plan_id="MAPLAN-TEST",
            orchestration_id="ORCH-TEST",
            plan_id="APLAN-TEST",
            decision_id="DINT-TEST",
            created_at=NOW,
            actions=(
                MultiAction(
                    action_id="MACT-DUP",
                    sequence=1,
                    action_type="a",
                    description="A",
                ),
                MultiAction(
                    action_id="MACT-DUP",
                    sequence=2,
                    action_type="b",
                    description="B",
                ),
            ),
        )


def test_build_is_deterministic_and_cached():
    engine = MultiActionExecutionPlanEngine()
    orchestration = make_orchestration()

    first = engine.build(orchestration)
    second = engine.build(orchestration)

    assert first is second
    assert len(engine.plans) == 1


def test_build_many():
    engine = MultiActionExecutionPlanEngine()

    first = make_orchestration()

    second_plan = ActionPlan(
        plan_id="APLAN-M33-2-B",
        decision_id="DINT-M33-2-B",
        created_at=NOW,
        decision_type="system_review",
        priority="normal",
        reason="Second coordinated plan.",
        steps=(
            ActionPlanStep(
                step_id="ASTEP-M33-2-B-1",
                sequence=1,
                action_type="system.check",
                description="Check system.",
                target_system_id="SYS-002",
            ),
        ),
    )

    second = ControlOrchestrationEngine().build(second_plan)

    results = engine.build_many((first, second))

    assert len(results) == 2
    assert results[0].plan_id == "APLAN-M33-2"
    assert results[1].plan_id == "APLAN-M33-2-B"
    assert all(not result.executable for result in results)
