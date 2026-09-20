from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import ActionPlan, ActionPlanStep
from yoma.office.decision_dependencies import (
    DecisionDependency,
    DecisionDependencyMap,
)
from yoma.office.control_orchestration import (
    ControlOrchestration,
    ControlOrchestrationEngine,
    OrchestrationStep,
)


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_plan(plan_id="APLAN-M33-1"):
    return ActionPlan(
        plan_id=plan_id,
        decision_id=f"DINT-{plan_id}",
        created_at=NOW,
        decision_type="workload_review",
        priority="high",
        reason="Operational workload requires coordinated control.",
        steps=(
            ActionPlanStep(
                step_id=f"ASTEP-{plan_id}-1",
                sequence=1,
                action_type="notify.manager",
                description="Notify manager.",
                target_user_id="EMP-001",
                parameters={"channel": "email"},
            ),
            ActionPlanStep(
                step_id=f"ASTEP-{plan_id}-2",
                sequence=2,
                action_type="review.workload",
                description="Review workload.",
                target_user_id="EMP-001",
            ),
        ),
        affected_user_ids=("EMP-001",),
        affected_system_ids=("SYS-001",),
    )


def make_dependency_map(plan):
    return DecisionDependencyMap(
        dependency_map_id=f"DMAP-{plan.plan_id}",
        plan_id=plan.plan_id,
        decision_id=plan.decision_id,
        dependencies=(
            DecisionDependency(
                dependency_id=f"DEP-{plan.plan_id}-EMP",
                dependency_type="user",
                entity_id="EMP-001",
                relationship="affected_by",
                reason="Employee is affected by the plan.",
            ),
        ),
        affected_user_ids=("EMP-001",),
        dependency_depth=1,
    )


def test_build_orchestration():
    engine = ControlOrchestrationEngine()
    plan = make_plan()

    result = engine.build(plan)

    assert result.orchestration_id == f"ORCH-{plan.plan_id}"
    assert result.plan_id == plan.plan_id
    assert result.decision_id == plan.decision_id


def test_steps_are_preserved_in_sequence():
    engine = ControlOrchestrationEngine()
    result = engine.build(make_plan())

    assert result.step_count == 2
    assert [step.sequence for step in result.steps] == [1, 2]
    assert result.action_types == (
        "notify.manager",
        "review.workload",
    )


def test_step_identity_is_deterministic():
    engine = ControlOrchestrationEngine()
    plan = make_plan()

    result = engine.build(plan)

    assert result.steps[0].step_id == f"OSTEP-{plan.plan_id}-1"
    assert result.steps[1].step_id == f"OSTEP-{plan.plan_id}-2"


def test_dependency_map_is_attached():
    engine = ControlOrchestrationEngine()
    plan = make_plan()
    dependency_map = make_dependency_map(plan)

    result = engine.build(plan, dependency_map)

    assert result.dependency_map_id == dependency_map.dependency_map_id
    assert result.steps[0].dependency_ids == (
        dependency_map.dependencies[0].dependency_id,
    )


def test_affected_entities_are_preserved():
    engine = ControlOrchestrationEngine()
    result = engine.build(make_plan())

    assert result.affected_user_ids == ("EMP-001",)
    assert result.affected_system_ids == ("SYS-001",)


def test_human_approval_is_mandatory():
    engine = ControlOrchestrationEngine()
    result = engine.build(make_plan())

    assert result.requires_human_approval is True
    assert result.executable is False
    assert all(
        step.requires_human_approval
        for step in result.steps
    )


def test_parameters_are_preserved():
    engine = ControlOrchestrationEngine()
    result = engine.build(make_plan())

    assert result.steps[0].parameters["channel"] == "email"


def test_dependency_mismatch_is_rejected():
    engine = ControlOrchestrationEngine()
    plan = make_plan("APLAN-A")
    dependency_map = make_dependency_map(make_plan("APLAN-B"))

    with pytest.raises(ValueError):
        engine.build(plan, dependency_map)


def test_build_is_deterministic_and_cached():
    engine = ControlOrchestrationEngine()
    plan = make_plan()

    first = engine.build(plan)
    second = engine.build(plan)

    assert first is second
    assert first.orchestration_id == second.orchestration_id
    assert len(engine.orchestrations) == 1


def test_build_many():
    engine = ControlOrchestrationEngine()

    plan_a = make_plan("APLAN-A")
    plan_b = make_plan("APLAN-B")

    results = engine.build_many(
        (plan_a, plan_b),
        (
            make_dependency_map(plan_a),
            make_dependency_map(plan_b),
        ),
    )

    assert len(results) == 2
    assert results[0].plan_id == "APLAN-A"
    assert results[1].plan_id == "APLAN-B"
    assert all(not item.executable for item in results)
