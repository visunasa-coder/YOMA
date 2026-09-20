from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_execution import ActionExecutionGateway
from yoma.office.action_planning import ActionPlan, ActionPlanStep
from yoma.office.approval_execution_bridge import ApprovalExecutionBridge
from yoma.office.execution_audit import ExecutionAuditRecorder
from yoma.office.execution_observation import (
    ExecutionResultObservationEngine,
)
from yoma.office.execution_policy import ExecutionPolicyEnforcer
from yoma.office.execution_reconciliation import (
    ExecutionOutcomeReconciliationEngine,
)
from yoma.office.execution_reliability import (
    ExecutionReliabilityIntelligence,
    ExecutionReliabilityIntelligenceEngine,
    ExecutionReliabilityMetrics,
)
from yoma.office.policy_constraints import PolicyConstraintEngine


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_plan(
    decision_id="DINT-M32-8",
    action_id="ACT-M32-8",
    action_type="workload.review",
):
    return ActionPlan(
        plan_id=f"APLAN-{decision_id}",
        decision_id=decision_id,
        created_at=NOW,
        decision_type="workload_review",
        priority="high",
        reason="Review workload.",
        steps=(
            ActionPlanStep(
                step_id=action_id,
                sequence=1,
                action_type=action_type,
                description="Review workload.",
                target_user_id="EMP-1",
                parameters={"mode": "review"},
            ),
        ),
        affected_user_ids=("EMP-1",),
        requires_human_approval=True,
    )


def make_reconciliation(
    *,
    decision_id="DINT-M32-8",
    action_id="ACT-M32-8",
    action_type="workload.review",
    expected_event_count=1,
    observed_event_ids=("EVT-1",),
    execution_status="succeeded",
    outcome_status="succeeded",
    success=True,
):
    plan = make_plan(
        decision_id=decision_id,
        action_id=action_id,
        action_type=action_type,
    )

    approval_engine = ActionApprovalEngine()
    workflow = approval_engine.create(plan)

    workflow = approval_engine.approve(
        workflow,
        reviewer_id="manager-1",
        decided_at=NOW,
        comment="Approved.",
    )

    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test",
        lambda **kwargs: {
            "action_id": kwargs["action_id"],
            "status": "done",
        },
    )

    bridge = ApprovalExecutionBridge(gateway)

    policy_result = ExecutionPolicyEnforcer(
        policy_engine=PolicyConstraintEngine(),
        execution_bridge=bridge,
    ).execute(
        workflow=workflow,
        plan=plan,
        executor_name="test",
        created_at=NOW,
    )

    trace = ExecutionAuditRecorder().record(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        actor="manager-1",
        created_at=NOW,
    )

    observation = ExecutionResultObservationEngine().observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
        event_ids=observed_event_ids,
    )

    if (
        execution_status != observation.execution_status
        or outcome_status != observation.outcome_status
        or success != observation.success
    ):
        observation = type(observation)(
            observation_id=observation.observation_id,
            trace_id=observation.trace_id,
            execution_id=observation.execution_id,
            workflow_id=observation.workflow_id,
            plan_id=observation.plan_id,
            decision_id=observation.decision_id,
            action_id=observation.action_id,
            action_type=observation.action_type,
            observed_at=observation.observed_at,
            execution_status=execution_status,
            outcome_status=outcome_status,
            success=success,
            output=observation.output,
            error=None if success else "execution failed",
            event_ids=tuple(observed_event_ids),
            evidence=observation.evidence,
        )

    return ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_event_count=expected_event_count,
        expected_success=success,
    )


def test_empty_data():
    result = ExecutionReliabilityIntelligenceEngine().analyze(())

    assert isinstance(result, ExecutionReliabilityIntelligence)
    assert isinstance(result.metrics, ExecutionReliabilityMetrics)
    assert result.metrics.total_executions == 0
    assert result.reliability_level == "insufficient_data"
    assert result.confidence == 0.0
    assert result.executable is False


def test_excellent_reliability():
    values = tuple(
        make_reconciliation(
            decision_id=f"DINT-M32-8-{i}",
            action_id=f"ACT-M32-8-{i}",
        )
        for i in range(5)
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert result.reliability_level == "excellent"
    assert result.metrics.success_rate == 1.0
    assert result.metrics.failure_rate == 0.0
    assert result.metrics.evidence_quality == 1.0


def test_reliable_reliability():
    values = tuple(
        make_reconciliation(
            decision_id=f"DINT-M32-8-R-{i}",
            action_id=f"ACT-M32-8-R-{i}",
        )
        for i in range(4)
    )

    values += (
        make_reconciliation(
            decision_id="DINT-M32-8-R-F",
            action_id="ACT-M32-8-R-F",
            expected_event_count=0,
            observed_event_ids=(),
            execution_status="failed",
            outcome_status="failed",
            success=False,
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert result.reliability_level == "reliable"
    assert result.metrics.total_executions == 5
    assert result.metrics.achieved_count == 4
    assert result.metrics.failed_count == 1
    assert result.metrics.success_rate == 0.8


def test_mixed_reliability():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-M1",
            action_id="ACT-M32-8-M1",
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-M2",
            action_id="ACT-M32-8-M2",
            expected_event_count=3,
            observed_event_ids=("EVT-1",),
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-M3",
            action_id="ACT-M32-8-M3",
            expected_event_count=0,
            observed_event_ids=(),
            execution_status="failed",
            outcome_status="failed",
            success=False,
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert result.reliability_level == "mixed"
    assert result.metrics.partial_count == 1
    assert result.metrics.failed_count == 1


def test_unreliable_reliability():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-U1",
            action_id="ACT-M32-8-U1",
            expected_event_count=0,
            observed_event_ids=(),
            execution_status="failed",
            outcome_status="failed",
            success=False,
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-U2",
            action_id="ACT-M32-8-U2",
            expected_event_count=0,
            observed_event_ids=(),
            execution_status="failed",
            outcome_status="failed",
            success=False,
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-U3",
            action_id="ACT-M32-8-U3",
            expected_event_count=0,
            observed_event_ids=(),
            execution_status="blocked",
            outcome_status="blocked",
            success=False,
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert result.reliability_level == "unreliable"
    assert result.requires_review is True


def test_insufficient_evidence_is_tracked():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-E1",
            action_id="ACT-M32-8-E1",
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-E2",
            action_id="ACT-M32-8-E2",
            expected_event_count=1,
            observed_event_ids=(),
            execution_status="succeeded",
            outcome_status="unknown",
            success=True,
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert result.metrics.insufficient_evidence_count == 1
    assert result.metrics.evidence_quality == 0.5
    assert "workload.review:insufficient_evidence" not in (
        result.failure_patterns
    )


def test_action_type_filtering():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-A1",
            action_id="ACT-M32-8-A1",
            action_type="workload.review",
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-A2",
            action_id="ACT-M32-8-A2",
            action_type="workload.review",
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-B1",
            action_id="ACT-M32-8-B1",
            action_type="meeting.review",
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(
        values,
        action_type="workload.review",
    )

    assert result.metrics.total_executions == 2
    assert result.metrics.action_type == "workload.review"
    assert result.action_types == ("workload.review",)


def test_failure_patterns():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-P1",
            action_id="ACT-M32-8-P1",
            expected_event_count=0,
            observed_event_ids=(),
            execution_status="failed",
            outcome_status="failed",
            success=False,
        ),
        make_reconciliation(
            decision_id="DINT-M32-8-P2",
            action_id="ACT-M32-8-P2",
            expected_event_count=3,
            observed_event_ids=("EVT-1",),
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert "workload.review:failed" in result.failure_patterns
    assert "workload.review:partially_achieved" in result.failure_patterns


def test_traceability_and_storage():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-T1",
            action_id="ACT-M32-8-T1",
        ),
    )

    engine = ExecutionReliabilityIntelligenceEngine()
    result = engine.analyze(values)

    assert result.metrics.reconciliation_ids == (
        values[0].reconciliation_id,
    )
    assert engine.get(result.intelligence_id) == result
    assert engine.intelligence == (result,)
    assert result.observations[0]["reconciliation_id"] == (
        values[0].reconciliation_id
    )


def test_human_governance():
    values = (
        make_reconciliation(
            decision_id="DINT-M32-8-G1",
            action_id="ACT-M32-8-G1",
        ),
    )

    result = ExecutionReliabilityIntelligenceEngine().analyze(values)

    assert result.requires_human_approval is True
    assert result.metrics.requires_human_approval is True
    assert result.executable is False
    assert result.metrics.executable is False
