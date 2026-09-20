from datetime import datetime, timezone

from yoma.office.integration.model import Integration
from yoma.office.multi_action_execution import (
    MultiAction,
    MultiActionExecutionPlan,
)
from yoma.office.cross_system_coordination import (
    CrossSystemCoordination,
    CrossSystemCoordinationEngine,
    SystemActionGroup,
    SystemCoordinationOrder,
)


def _plan(actions):
    return MultiActionExecutionPlan(
        execution_plan_id="MAPLAN-001",
        orchestration_id="ORCH-001",
        plan_id="PLAN-001",
        decision_id="DINT-001",
        created_at=datetime.now(timezone.utc),
        actions=tuple(actions),
    )


def _action(
    action_id,
    sequence,
    system,
    dependencies=(),
):
    return MultiAction(
        action_id=action_id,
        sequence=sequence,
        action_type=f"test.{action_id}",
        description=f"Action {action_id}",
        target_system_id=system,
        dependency_ids=tuple(dependencies),
    )


def test_single_system_group():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "gmail", ("MACT-1",)),
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert isinstance(result, CrossSystemCoordination)
    assert result.participating_system_ids == ("gmail",)
    assert result.groups[0].action_ids == ("MACT-1", "MACT-2")
    assert result.action_count == 2
    assert result.system_count == 1


def test_multiple_systems_are_grouped():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "slack"),
        _action("MACT-3", 3, "calendar"),
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert result.participating_system_ids == (
        "calendar",
        "gmail",
        "slack",
    )
    assert result.multi_system
    assert result.system_count == 3
    assert result.action_count == 3


def test_cross_system_dependency_is_derived():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "slack", ("MACT-1",)),
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert result.system_dependencies["slack"] == ("gmail",)
    assert result.system_dependencies["gmail"] == ()
    assert result.coordination_order.ordered_system_ids == (
        "gmail",
        "slack",
    )


def test_same_system_dependency_does_not_create_system_dependency():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "gmail", ("MACT-1",)),
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert result.system_dependencies["gmail"] == ()


def test_existing_integrations_resolve_systems():
    integrations = (
        Integration("gmail", "google", "communication"),
        Integration("slack", "slack", "communication"),
    )

    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "slack"),
    ])

    result = CrossSystemCoordinationEngine(
        integrations=integrations
    ).coordinate(plan)

    assert result.unresolved_system_ids == ()
    assert result.requires_review is False


def test_missing_integration_is_reported():
    integrations = (
        Integration("gmail", "google", "communication"),
    )

    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "slack"),
    ])

    result = CrossSystemCoordinationEngine(
        integrations=integrations
    ).coordinate(plan)

    assert result.unresolved_system_ids == ("slack",)
    assert result.requires_review is True


def test_unspecified_system_is_unresolved():
    plan = _plan([
        MultiAction(
            action_id="MACT-1",
            sequence=1,
            action_type="test.action",
            description="Unspecified system",
        )
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert result.participating_system_ids == ("UNSPECIFIED",)
    assert result.unresolved_system_ids == ("UNSPECIFIED",)
    assert result.requires_review is True


def test_deterministic_ids_and_cache():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
    ])

    engine = CrossSystemCoordinationEngine()

    first = engine.coordinate(plan)
    second = engine.coordinate(plan)

    assert first is second
    assert first.coordination_id == second.coordination_id
    assert first.groups[0].group_id == (
        "SGRP-MAPLAN-001-gmail"
    )
    assert first.coordination_order.order_id.startswith(
        "SYSORDER-XCOORD-"
    )


def test_dependency_levels_are_deterministic():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "slack", ("MACT-1",)),
        _action("MACT-3", 3, "calendar", ("MACT-2",)),
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert result.coordination_order.dependency_levels == (
        ("gmail",),
        ("slack",),
        ("calendar",),
    )


def test_human_approval_and_non_execution_invariants():
    plan = _plan([
        _action("MACT-1", 1, "gmail"),
        _action("MACT-2", 2, "slack"),
    ])

    result = CrossSystemCoordinationEngine().coordinate(plan)

    assert result.requires_human_approval is True
    assert result.executable is False
    assert result.coordination_order.requires_human_approval is True
    assert result.coordination_order.executable is False

    for group in result.groups:
        assert group.requires_human_approval is True
        assert group.executable is False
