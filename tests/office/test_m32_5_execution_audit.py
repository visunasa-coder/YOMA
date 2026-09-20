from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_execution import ActionExecutionGateway
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.approval_execution_bridge import ApprovalExecutionBridge
from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.execution_audit import ExecutionAuditRecorder
from yoma.office.execution_policy import ExecutionPolicyEnforcer
from yoma.office.governance.policy import AuditLog
from yoma.office.policy_constraints import (
    PolicyConstraint,
    PolicyConstraintEngine,
)


TEST_TIME = datetime(
    2026,
    9,
    6,
    tzinfo=timezone.utc,
)


def _decision(
    decision_id: str = "DINT-M32-5",
) -> DecisionIntelligence:
    return DecisionIntelligence(
        decision_id=decision_id,
        decision_type="workload_review",
        created_at=TEST_TIME,
        organization_id="ORG-1",
        user_id="EMP-1",
        situation_type="workload_pressure",
        priority="high",
        confidence=0.9,
        current_intelligence_available=True,
        recommendation_type="workload_review",
        recommendation_reason="Review workload.",
    )


def _approved_plan():
    decision = _decision()

    plan = ActionPlanningEngine().build(decision)

    approvals = ActionApprovalEngine()
    workflow = approvals.create(plan)

    workflow = approvals.approve(
        workflow,
        reviewer_id="ADMIN-1",
        decided_at=TEST_TIME,
        comment="Approved.",
    )

    return plan, workflow


def _policy_result(
    blocked: bool = False,
):
    plan, workflow = _approved_plan()

    calls = []

    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        lambda **kwargs: (
            calls.append(kwargs)
            or {"ok": True}
        ),
    )

    if blocked:
        constraints = (
            PolicyConstraint(
                constraint_id="POL-BLOCK-M32-5",
                constraint_type="execution",
                description="Execution is blocked.",
                allowed=False,
                priorities=("high",),
            ),
        )
    else:
        constraints = ()

    enforcer = ExecutionPolicyEnforcer(
        PolicyConstraintEngine(constraints),
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    return plan, workflow, result, calls


def test_records_successful_execution_trace():
    plan, workflow, result, _ = _policy_result()

    recorder = ExecutionAuditRecorder()

    trace = recorder.record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert trace.executed is True
    assert trace.blocked is False
    assert trace.policy_status == "allowed"
    assert trace.execution_status == "succeeded"


def test_records_blocked_execution_trace():
    plan, workflow, result, calls = _policy_result(
        blocked=True,
    )

    recorder = ExecutionAuditRecorder()

    trace = recorder.record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert trace.executed is False
    assert trace.blocked is True
    assert trace.execution_status == "blocked"
    assert calls == []


def test_trace_links_plan_and_decision():
    plan, workflow, result, _ = _policy_result()

    trace = ExecutionAuditRecorder().record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert trace.plan_id == plan.plan_id
    assert trace.decision_id == plan.decision_id


def test_trace_links_workflow_and_approval():
    plan, workflow, result, _ = _policy_result()

    trace = ExecutionAuditRecorder().record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert trace.workflow_id == workflow.workflow_id
    assert trace.approval_id == (
        workflow.approval_history[-1].approval_id
    )


def test_trace_contains_execution_id_when_executed():
    plan, workflow, result, _ = _policy_result()

    trace = ExecutionAuditRecorder().record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert trace.metadata["execution_id"] == (
        result.execution.execution_id
    )


def test_blocked_trace_has_no_execution_id():
    plan, workflow, result, _ = _policy_result(
        blocked=True,
    )

    trace = ExecutionAuditRecorder().record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert trace.metadata["execution_id"] is None


def test_audit_log_receives_trace():
    plan, workflow, result, _ = _policy_result()

    audit_log = AuditLog()
    recorder = ExecutionAuditRecorder(audit_log)

    trace = recorder.record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    records = audit_log.list()

    assert len(records) == 1
    assert records[0].audit_id == f"AUDIT-{trace.trace_id}"
    assert records[0].request_id == workflow.workflow_id


def test_audit_trace_is_retrievable():
    plan, workflow, result, _ = _policy_result()

    recorder = ExecutionAuditRecorder()

    trace = recorder.record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    assert recorder.get_trace(trace.trace_id) == trace
    assert recorder.traces == (trace,)


def test_sensitive_metadata_is_sanitized_by_audit_log():
    plan, workflow, result, _ = _policy_result()

    audit_log = AuditLog()
    recorder = ExecutionAuditRecorder(audit_log)

    recorder.record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    audit = audit_log.list()[0]

    assert "token" not in audit.metadata
    assert "secret" not in audit.metadata
    assert "password" not in audit.metadata


def test_duplicate_trace_is_rejected():
    plan, workflow, result, _ = _policy_result()

    recorder = ExecutionAuditRecorder()

    recorder.record(
        workflow=workflow,
        plan=plan,
        policy_result=result,
        actor="ADMIN-1",
        created_at=TEST_TIME,
    )

    with pytest.raises(ValueError):
        recorder.record(
            workflow=workflow,
            plan=plan,
            policy_result=result,
            actor="ADMIN-1",
            created_at=TEST_TIME,
        )
