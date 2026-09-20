from datetime import datetime, timezone

import pytest

from yoma.office.multi_action_execution import (
    MultiAction,
    MultiActionExecutionPlan,
)
from yoma.office.dependency_aware_execution import (
    DependencyAwareExecutionEngine,
)
from yoma.office.transaction_rollback import (
    RollbackAction,
    TransactionBoundary,
    TransactionRollbackPlan,
    TransactionIntelligence,
    TransactionRollbackIntelligenceEngine,
)


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_plan():
    return MultiActionExecutionPlan(
        execution_plan_id="MAPLAN-M33-4",
        orchestration_id="ORCH-M33-4",
        plan_id="APLAN-M33-4",
        decision_id="DINT-M33-4",
        created_at=NOW,
        actions=(
            MultiAction(
                action_id="MACT-A",
                sequence=1,
                action_type="prepare",
                description="Prepare operation.",
            ),
            MultiAction(
                action_id="MACT-B",
                sequence=2,
                action_type="update",
                description="Update resource.",
                dependency_ids=("MACT-A",),
            ),
            MultiAction(
                action_id="MACT-C",
                sequence=3,
                action_type="notify",
                description="Notify user.",
                dependency_ids=("MACT-B",),
            ),
        ),
    )


def test_transaction_is_created():
    plan = make_plan()
    order = DependencyAwareExecutionEngine().order(plan)

    result = TransactionRollbackIntelligenceEngine().build(
        plan,
        order,
    )

    assert result.transaction_id == "TX-MAPLAN-M33-4"
    assert result.execution_plan_id == plan.execution_plan_id


def test_transaction_boundary_contains_all_actions():
    plan = make_plan()
    result = TransactionRollbackIntelligenceEngine().build(plan)

    assert result.boundary.action_ids == (
        "MACT-A",
        "MACT-B",
        "MACT-C",
    )
    assert result.boundary.atomic is True
    assert result.boundary.rollback_supported is True


def test_dependency_order_is_preserved():
    plan = make_plan()
    order = DependencyAwareExecutionEngine().order(plan)

    result = TransactionRollbackIntelligenceEngine().build(
        plan,
        order,
    )

    assert result.ordered_action_ids == (
        "MACT-A",
        "MACT-B",
        "MACT-C",
    )


def test_initial_transaction_needs_no_rollback():
    result = TransactionRollbackIntelligenceEngine().build(
        make_plan()
    )

    assert result.rollback_required is False
    assert result.rollback_plan.status == "planned"
    assert result.rollback_plan.rollback_count == 0


def test_rollback_plan_uses_reverse_commit_order():
    engine = TransactionRollbackIntelligenceEngine()
    plan = make_plan()

    result = engine.plan_rollback(
        plan,
        failed_action_id="MACT-C",
        committed_action_ids=("MACT-A", "MACT-B"),
    )

    assert result.rollback_required is True
    assert result.status == "rollback_required"
    assert [item.source_action_id for item in result.rollback_actions] == [
        "MACT-B",
        "MACT-A",
    ]


def test_rollback_action_ids_are_deterministic():
    result = TransactionRollbackIntelligenceEngine().plan_rollback(
        make_plan(),
        failed_action_id="MACT-C",
        committed_action_ids=("MACT-A", "MACT-B"),
    )

    assert [item.rollback_id for item in result.rollback_actions] == [
        "RBAC-MAPLAN-M33-4-1",
        "RBAC-MAPLAN-M33-4-2",
    ]


def test_rollback_actions_are_not_executable():
    result = TransactionRollbackIntelligenceEngine().plan_rollback(
        make_plan(),
        failed_action_id="MACT-C",
        committed_action_ids=("MACT-A", "MACT-B"),
    )

    assert result.requires_human_approval is True
    assert result.executable is False
    assert all(
        item.requires_human_approval
        for item in result.rollback_actions
    )
    assert all(
        not item.executable
        for item in result.rollback_actions
    )


def test_invalid_failed_action_is_rejected():
    with pytest.raises(ValueError):
        TransactionRollbackIntelligenceEngine().plan_rollback(
            make_plan(),
            failed_action_id="MACT-MISSING",
            committed_action_ids=("MACT-A",),
        )


def test_unknown_committed_action_is_rejected():
    with pytest.raises(ValueError):
        TransactionRollbackIntelligenceEngine().plan_rollback(
            make_plan(),
            failed_action_id="MACT-C",
            committed_action_ids=("MACT-A", "MACT-MISSING"),
        )


def test_transaction_is_deterministic_and_cached():
    engine = TransactionRollbackIntelligenceEngine()
    plan = make_plan()

    first = engine.build(plan)
    second = engine.build(plan)

    assert first is second
    assert first.transaction_id == second.transaction_id
    assert len(engine.transactions) == 1
    assert first.requires_human_approval is True
    assert first.executable is False
