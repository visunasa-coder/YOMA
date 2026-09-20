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
    ExecutionOutcomeReconciliation,
    ExecutionOutcomeReconciliationEngine,
)
from yoma.office.policy_constraints import PolicyConstraintEngine


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_plan(decision_id="DINT-M32-7"):
    return ActionPlan(
        plan_id=f"APLAN-{decision_id}",
        decision_id=decision_id,
        created_at=NOW,
        decision_type="workload_review",
        priority="high",
        reason="Review workload.",
        steps=(
            ActionPlanStep(
                step_id="ACT-M32-7",
                sequence=1,
                action_type="workload.review",
                description="Review workload.",
                target_user_id="EMP-1",
                parameters={"mode": "review"},
            ),
        ),
        affected_user_ids=("EMP-1",),
        requires_human_approval=True,
    )


def make_pipeline(executor_output=None):
    plan = make_plan()

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
        lambda **kwargs: (
            executor_output
            if executor_output is not None
            else {
                "action_id": kwargs["action_id"],
                "status": "done",
            }
        ),
    )

    bridge = ApprovalExecutionBridge(gateway)

    enforcer = ExecutionPolicyEnforcer(
        policy_engine=PolicyConstraintEngine(),
        execution_bridge=bridge,
    )

    policy_result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test",
        created_at=NOW,
    )

    audit = ExecutionAuditRecorder()

    trace = audit.record(
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
        event_ids=("EVT-1",),
    )

    return plan, workflow, trace, observation


def test_achieved():
    plan, workflow, trace, observation = make_pipeline()

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_event_count=1,
        expected_success=True,
    )

    assert isinstance(result, ExecutionOutcomeReconciliation)
    assert result.status == "achieved"
    assert result.achieved is True
    assert result.requires_review is False
    assert result.executable is False


def test_partial_achievement():
    plan, workflow, trace, observation = make_pipeline()

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_event_count=3,
        expected_success=True,
    )

    assert result.status == "partially_achieved"
    assert result.observed_event_count == 1
    assert result.expected_event_count == 3


def test_insufficient_evidence():
    plan, workflow, trace, observation = make_pipeline()

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
        execution_status="succeeded",
        outcome_status="unknown",
        success=True,
        output=observation.output,
        error=observation.error,
        event_ids=(),
        evidence=observation.evidence,
    )

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_event_count=1,
    )

    assert result.status == "insufficient_evidence"
    assert result.requires_review is True


def test_failed():
    plan, workflow, trace, observation = make_pipeline()

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
        execution_status="failed",
        outcome_status="failed",
        success=False,
        output={},
        error="executor failed",
        event_ids=(),
        evidence={},
    )

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
    )

    assert result.status == "failed"
    assert result.failed is True


def test_unexpected_blocked():
    plan, workflow, trace, observation = make_pipeline()

    observation = type(observation)(
        observation_id=observation.observation_id,
        trace_id=observation.trace_id,
        execution_id=None,
        workflow_id=observation.workflow_id,
        plan_id=observation.plan_id,
        decision_id=observation.decision_id,
        action_id=observation.action_id,
        action_type=observation.action_type,
        observed_at=observation.observed_at,
        execution_status="blocked",
        outcome_status="blocked",
        success=False,
        output={},
        error="policy blocked",
        event_ids=(),
        evidence={},
    )

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
    )

    assert result.status == "unexpected"
    assert result.requires_review is True


def test_expected_success_mismatch():
    plan, workflow, trace, observation = make_pipeline()

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_success=False,
    )

    assert result.status == "unexpected"


def test_traceability():
    plan, workflow, trace, observation = make_pipeline()

    result = ExecutionOutcomeReconciliationEngine().reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_event_count=1,
    )

    assert result.trace_id == trace.trace_id
    assert result.execution_id == observation.execution_id
    assert result.workflow_id == workflow.workflow_id
    assert result.plan_id == plan.plan_id
    assert result.decision_id == plan.decision_id
    assert result.action_id == observation.action_id
    assert result.event_ids == ("EVT-1",)


def test_retrieval_and_duplicate_protection():
    plan, workflow, trace, observation = make_pipeline()

    engine = ExecutionOutcomeReconciliationEngine()

    result = engine.reconcile(
        workflow=workflow,
        plan=plan,
        audit_trace=trace,
        observation=observation,
        expected_event_count=1,
    )

    assert engine.get_reconciliation(result.reconciliation_id) == result
    assert engine.reconciliations == (result,)

    with pytest.raises(ValueError, match="reconciliation already exists"):
        engine.reconcile(
            workflow=workflow,
            plan=plan,
            audit_trace=trace,
            observation=observation,
            expected_event_count=1,
        )


def test_identity_validation():
    plan, workflow, trace, observation = make_pipeline()

    other_plan = make_plan("DINT-M32-7-OTHER")

    with pytest.raises(
        ValueError,
        match="workflow and plan IDs do not match",
    ):
        ExecutionOutcomeReconciliationEngine().reconcile(
            workflow=workflow,
            plan=other_plan,
            audit_trace=trace,
            observation=observation,
        )


def test_reconcile_many():
    plan, workflow, trace, observation = make_pipeline()

    engine = ExecutionOutcomeReconciliationEngine()

    results = engine.reconcile_many(
        [
            (
                workflow,
                plan,
                trace,
                observation,
                1,
                True,
                {"source": "m32.7"},
            )
        ]
    )

    assert len(results) == 1
    assert results[0].status == "achieved"
    assert results[0].evidence["source"] == "m32.7"
