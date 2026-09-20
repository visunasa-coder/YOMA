from datetime import datetime, timezone

import pytest

from yoma.office.multi_action_execution import (
    MultiAction,
    MultiActionExecutionPlan,
)
from yoma.office.dependency_aware_execution import (
    DependencyAwareExecutionEngine,
    DependencyExecutionAnalysis,
    ExecutionOrder,
)


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_plan(
    actions,
    plan_id="MAPLAN-M33-3",
):
    return MultiActionExecutionPlan(
        execution_plan_id=plan_id,
        orchestration_id="ORCH-M33-3",
        plan_id="APLAN-M33-3",
        decision_id="DINT-M33-3",
        created_at=NOW,
        actions=tuple(actions),
    )


def test_sequential_order_without_dependencies():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
            ),
            MultiAction(
                action_id="MACT-B",
                sequence=2,
                action_type="second",
                description="Second",
            ),
        )
    )

    result = DependencyAwareExecutionEngine().order(plan)

    assert result.ordered_action_ids == (
        "MACT-A",
        "MACT-B",
    )


def test_dependency_changes_order():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-B",
                sequence=1,
                action_type="second",
                description="Second",
                dependency_ids=("MACT-A",),
            ),
            MultiAction(
                action_id="MACT-A",
                sequence=2,
                action_type="first",
                description="First",
            ),
        )
    )

    result = DependencyAwareExecutionEngine().order(plan)

    assert result.ordered_action_ids == (
        "MACT-A",
        "MACT-B",
    )


def test_dependency_levels_are_generated():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
            ),
            MultiAction(
                action_id="MACT-B",
                sequence=2,
                action_type="second",
                description="Second",
                dependency_ids=("MACT-A",),
            ),
            MultiAction(
                action_id="MACT-C",
                sequence=3,
                action_type="third",
                description="Third",
                dependency_ids=("MACT-B",),
            ),
        )
    )

    result = DependencyAwareExecutionEngine().order(plan)

    assert result.dependency_levels == (
        ("MACT-A",),
        ("MACT-B",),
        ("MACT-C",),
    )


def test_independent_actions_share_level():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
            ),
            MultiAction(
                action_id="MACT-B",
                sequence=2,
                action_type="second",
                description="Second",
            ),
        )
    )

    result = DependencyAwareExecutionEngine().order(plan)

    assert result.dependency_levels == (
        ("MACT-A", "MACT-B"),
    )


def test_missing_dependency_is_blocked():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
                dependency_ids=("MACT-MISSING",),
            ),
        )
    )

    result = DependencyAwareExecutionEngine().order(plan)

    assert result.ordered_action_ids == ()
    assert result.blocked_action_ids == ("MACT-A",)
    assert result.missing_dependency_ids == ("MACT-MISSING",)


def test_circular_dependency_is_rejected():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
                dependency_ids=("MACT-B",),
            ),
            MultiAction(
                action_id="MACT-B",
                sequence=2,
                action_type="second",
                description="Second",
                dependency_ids=("MACT-A",),
            ),
        )
    )

    with pytest.raises(ValueError, match="circular dependency"):
        DependencyAwareExecutionEngine().order(plan)


def test_analysis_identifies_ready_actions():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
            ),
            MultiAction(
                action_id="MACT-B",
                sequence=2,
                action_type="second",
                description="Second",
                dependency_ids=("MACT-A",),
            ),
        )
    )

    result = DependencyAwareExecutionEngine().analyze(plan)

    assert result.ready_action_ids == ("MACT-A",)
    assert result.blocked_action_ids == ()
    assert result.circular_dependency is False
    assert result.dependency_count == 1


def test_analysis_detects_missing_dependency():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
                dependency_ids=("MACT-MISSING",),
            ),
        )
    )

    result = DependencyAwareExecutionEngine().analyze(plan)

    assert result.missing_dependency_ids == ("MACT-MISSING",)
    assert result.requires_review is True


def test_human_approval_and_non_execution_are_preserved():
    plan = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
            ),
        )
    )

    engine = DependencyAwareExecutionEngine()

    order = engine.order(plan)
    analysis = engine.analyze(plan)

    assert order.requires_human_approval is True
    assert order.executable is False
    assert analysis.requires_human_approval is True
    assert analysis.executable is False


def test_order_many_and_deterministic_cache():
    engine = DependencyAwareExecutionEngine()

    plan_a = make_plan(
        (
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="first",
                description="First",
            ),
        ),
        "MAPLAN-A",
    )

    plan_b = make_plan(
        (
            MultiAction(
                action_id="MACT-B",
                sequence=1,
                action_type="second",
                description="Second",
            ),
        ),
        "MAPLAN-B",
    )

    first = engine.order(plan_a)
    second = engine.order(plan_a)

    results = engine.order_many((plan_a, plan_b))

    assert first is second
    assert len(results) == 2
    assert results[0].execution_plan_id == "MAPLAN-A"
    assert results[1].execution_plan_id == "MAPLAN-B"
    assert all(not item.executable for item in results)
