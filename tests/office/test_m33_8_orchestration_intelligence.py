from datetime import datetime, timedelta, timezone

from yoma.office.multi_action_execution import (
    MultiAction,
    MultiActionExecutionPlan,
)
from yoma.office.dependency_aware_execution import (
    DependencyAwareExecutionEngine,
)
from yoma.office.transaction_rollback import (
    TransactionRollbackIntelligenceEngine,
)
from yoma.office.execution_scheduling import (
    ExecutionSchedulingEngine,
)
from yoma.office.cross_system_coordination import (
    CrossSystemCoordinationEngine,
)
from yoma.office.integration.model import Integration
from yoma.office.orchestration_intelligence import (
    OrchestrationIntelligence,
    OrchestrationIntelligenceEngine,
)


def _plan(actions):
    return MultiActionExecutionPlan(
        execution_plan_id="MAPLAN-INT-001",
        orchestration_id="ORCH-INT-001",
        plan_id="PLAN-INT-001",
        decision_id="DINT-INT-001",
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


def _context(actions, integrations=()):
    plan = _plan(actions)

    order = DependencyAwareExecutionEngine().order(plan)

    transaction = (
        TransactionRollbackIntelligenceEngine()
        .build(plan, order)
    )

    coordination = (
        CrossSystemCoordinationEngine(
            integrations=tuple(integrations)
        ).coordinate(plan)
    )

    scheduled_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=1)
    )

    schedule_result = (
        ExecutionSchedulingEngine()
        .schedule(
            plan,
            scheduled_at=scheduled_at,
            created_at=datetime.now(timezone.utc),
        )
    )

    return (
        plan,
        order,
        transaction,
        coordination,
        schedule_result.schedule,
    )


class _PendingApproval:
    def __init__(self, execution_plan_id):
        self.queue_item_id = "AQITEM-INT-001"
        self.execution_plan_id = execution_plan_id
        self.status = "pending"


def test_healthy_orchestration():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
        ]
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
    )

    assert isinstance(result, OrchestrationIntelligence)
    assert result.health.status == "healthy"
    assert result.health.risk_score == 0.0
    assert result.signal_count == 0


def test_multiple_systems_are_monitored():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
            _action("MACT-INT-2", 2, "slack"),
        ]
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
    )

    assert result.health.participating_system_count == 2
    assert result.coordination_id == coordination.coordination_id
    assert result.health.status == "healthy"


def test_missing_dependency_creates_blocked_intelligence():
    plan = _plan(
        [
            _action(
                "MACT-INT-1",
                1,
                "gmail",
                ("MACT-MISSING",),
            )
        ]
    )

    order = DependencyAwareExecutionEngine().order(plan)

    # A blocked dependency plan cannot be scheduled or wrapped in a
    # transaction by M33.4. M33.8 therefore monitors the dependency
    # analysis directly for this case.
    from yoma.office.dependency_aware_execution import (
        DependencyExecutionAnalysis,
    )

    analysis = DependencyExecutionAnalysis(
        analysis_id="DEPAN-MAPLAN-INT-001",
        execution_plan_id=plan.execution_plan_id,
        ready_action_ids=(),
        blocked_action_ids=("MACT-INT-1",),
        missing_dependency_ids=("MACT-MISSING",),
        dependency_count=1,
    )

    assert analysis.missing_dependency_ids == (
        "MACT-MISSING",
    )
    assert analysis.blocked_action_ids == (
        "MACT-INT-1",
    )
    assert analysis.requires_review is True

    assert order.missing_dependency_ids == (
        "MACT-MISSING",
    )


def test_blocked_dependency_is_visible_in_execution_order():
    plan = _plan(
        [
            _action(
                "MACT-INT-1",
                1,
                "gmail",
                ("MACT-MISSING",),
            )
        ]
    )

    order = DependencyAwareExecutionEngine().order(plan)

    assert order.ordered_action_ids == ()
    assert order.blocked_action_ids == (
        "MACT-INT-1",
    )
    assert order.missing_dependency_ids == (
        "MACT-MISSING",
    )


def test_unresolved_system_creates_signal():
    integrations = (
        Integration(
            "gmail",
            "google",
            "communication",
        ),
    )

    plan, order, transaction, coordination, schedule = _context(
        [
            _action(
                "MACT-INT-1",
                1,
                "unknown-system",
            ),
        ],
        integrations=integrations,
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
    )

    assert coordination.unresolved_system_ids == (
        "unknown-system",
    )

    assert result.health.unresolved_system_count == 1

    assert any(
        signal.signal_type == "system.unresolved"
        for signal in result.monitoring_signals
    )


def test_pending_approval_is_monitored():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
        ]
    )

    approval = _PendingApproval(
        plan.execution_plan_id
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
        (approval,),
    )

    assert result.approval_pending_count == 1

    assert any(
        signal.signal_type == "approval.pending"
        for signal in result.monitoring_signals
    )

    assert result.requires_review is True


def test_approval_does_not_equal_execution():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
        ]
    )

    approval = _PendingApproval(
        plan.execution_plan_id
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
        (approval,),
    )

    assert result.progress.total_actions == 1
    assert result.progress.completed_actions == 0
    assert result.progress.progress_ratio == 0.0


def test_rollback_required_is_detected():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
            _action(
                "MACT-INT-2",
                2,
                "slack",
                ("MACT-INT-1",),
            ),
        ]
    )

    rollback_plan = (
        TransactionRollbackIntelligenceEngine()
        .plan_rollback(
            plan,
            failed_action_id="MACT-INT-2",
            committed_action_ids=("MACT-INT-1",),
        )
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        rollback_plan,
        coordination,
        schedule,
    )

    assert rollback_plan.rollback_required is True
    assert result.health.rollback_required is True
    assert result.health.status == "failed"

    assert any(
        signal.signal_type
        == "transaction.rollback_required"
        for signal in result.monitoring_signals
    )


def test_deterministic_identity_and_cache():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
        ]
    )

    engine = OrchestrationIntelligenceEngine()

    first = engine.analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
    )

    second = engine.analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
    )

    assert first is second

    assert first.intelligence_id == (
        "OINT-MAPLAN-INT-001"
    )

    assert first.health.health_id == (
        "OHEALTH-MAPLAN-INT-001"
    )

    assert first.progress.progress_id == (
        "OPROG-MAPLAN-INT-001"
    )


def test_non_execution_invariants():
    plan, order, transaction, coordination, schedule = _context(
        [
            _action("MACT-INT-1", 1, "gmail"),
        ]
    )

    result = OrchestrationIntelligenceEngine().analyze(
        plan,
        order,
        transaction,
        coordination,
        schedule,
    )

    assert result.requires_human_approval is True
    assert result.executable is False

    assert result.health.requires_human_approval is True
    assert result.health.executable is False

    assert result.progress.requires_human_approval is True
    assert result.progress.executable is False

    for signal in result.monitoring_signals:
        assert signal.requires_human_approval is True
        assert signal.executable is False
