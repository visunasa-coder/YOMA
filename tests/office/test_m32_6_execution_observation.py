from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_execution import ActionExecutionGateway
from yoma.office.action_planning import ActionPlan, ActionPlanStep
from yoma.office.approval_execution_bridge import ApprovalExecutionBridge
from yoma.office.execution_audit import ExecutionAuditRecorder
from yoma.office.execution_observation import (
    ExecutionResultObservation,
    ExecutionResultObservationEngine,
)
from yoma.office.execution_policy import ExecutionPolicyEnforcer
from yoma.office.policy_constraints import PolicyConstraintEngine


NOW = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)


def make_plan(decision_id="DINT-M32-6"):
    return ActionPlan(
        plan_id=f"APLAN-{decision_id}",
        decision_id=decision_id,
        created_at=NOW,
        decision_type="workload_review",
        priority="high",
        reason="Review workload.",
        steps=(
            ActionPlanStep(
                step_id="ACT-M32-6",
                sequence=1,
                action_type="workload.review",
                description="Review workload.",
                target_user_id="EMP-1",
                parameters={"mode": "review"},
            ),
        ),
        evidence=(),
        affected_user_ids=("EMP-1",),
        affected_system_ids=(),
        requires_human_approval=True,
    )


def execute_pipeline():
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
        lambda **kwargs: {
            "action_id": kwargs["action_id"],
            "status": "done",
        },
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

    return plan, workflow, policy_result, trace


def test_success_observation():
    plan, workflow, policy_result, trace = execute_pipeline()

    result = ExecutionResultObservationEngine().observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
        event_ids=("EVT-1",),
    )

    assert isinstance(result, ExecutionResultObservation)
    assert result.action_id == "ACT-M32-6"
    assert result.execution_status == "succeeded"
    assert result.outcome_status == "succeeded"
    assert result.success is True
    assert result.executable is False


def test_execution_id_preserved():
    plan, workflow, policy_result, trace = execute_pipeline()

    result = ExecutionResultObservationEngine().observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
    )

    assert result.execution_id == policy_result.execution.execution_id


def test_output_preserved():
    plan, workflow, policy_result, trace = execute_pipeline()

    result = ExecutionResultObservationEngine().observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
    )

    assert result.output["status"] == "done"


def test_mismatched_plan_rejected():
    _, workflow, policy_result, trace = execute_pipeline()

    other_plan = make_plan("DINT-M32-6-OTHER")

    with pytest.raises(
        ValueError,
        match="workflow and plan IDs do not match",
    ):
        ExecutionResultObservationEngine().observe(
            workflow=workflow,
            plan=other_plan,
            policy_result=policy_result,
            audit_trace=trace,
            observed_at=NOW,
        )


def test_mismatched_trace_rejected():
    plan, workflow, policy_result, trace = execute_pipeline()

    bad_trace = type(trace)(
        trace_id="TRACE-AWF-BAD-ACT-M32-6",
        plan_id=trace.plan_id,
        decision_id=trace.decision_id,
        workflow_id="AWF-BAD",
        approval_id=trace.approval_id,
        action_id=trace.action_id,
        action_type=trace.action_type,
        policy_status=trace.policy_status,
        execution_status=trace.execution_status,
        executed=trace.executed,
        blocked=trace.blocked,
        created_at=trace.created_at,
    )

    with pytest.raises(
        ValueError,
        match="audit trace and workflow IDs",
    ):
        ExecutionResultObservationEngine().observe(
            workflow=workflow,
            plan=plan,
            policy_result=policy_result,
            audit_trace=bad_trace,
            observed_at=NOW,
        )


def test_observation_retrievable():
    plan, workflow, policy_result, trace = execute_pipeline()

    engine = ExecutionResultObservationEngine()

    result = engine.observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
    )

    assert engine.get_observation(result.observation_id) == result
    assert engine.observations == (result,)


def test_duplicate_observation_rejected():
    plan, workflow, policy_result, trace = execute_pipeline()

    engine = ExecutionResultObservationEngine()

    engine.observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
    )

    with pytest.raises(ValueError, match="already exists"):
        engine.observe(
            workflow=workflow,
            plan=plan,
            policy_result=policy_result,
            audit_trace=trace,
            observed_at=NOW,
        )


def test_closed_loop_integration():
    plan, workflow, policy_result, trace = execute_pipeline()

    engine = ExecutionResultObservationEngine()

    result = engine.observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
        event_ids=("EVT-1",),
    )

    loop = engine.observe_closed_loop(
        workflow=workflow,
        execution_observation=result,
        expected_event_count=1,
    )

    assert loop.outcome_status == "observed"
    assert loop.observed_event_count == 1
    assert loop.matches_expectation is True


def test_observer_never_executes():
    plan, workflow, policy_result, trace = execute_pipeline()

    engine = ExecutionResultObservationEngine()

    engine.observe(
        workflow=workflow,
        plan=plan,
        policy_result=policy_result,
        audit_trace=trace,
        observed_at=NOW,
    )

    fresh_gateway = ActionExecutionGateway()

    assert fresh_gateway.records == ()


def test_observe_many():
    plan, workflow, policy_result, trace = execute_pipeline()

    engine = ExecutionResultObservationEngine()

    results = engine.observe_many(
        [
            (
                workflow,
                plan,
                policy_result,
                trace,
                NOW,
            )
        ]
    )

    assert len(results) == 1
    assert results[0] == engine.observations[0]
