from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_execution import ActionExecutionGateway
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.approval_execution_bridge import ApprovalExecutionBridge
from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.execution_policy import ExecutionPolicyEnforcer
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
    decision_id: str = "DINT-M32-4",
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


def _approved_plan(
    decision_id: str = "DINT-M32-4",
):
    decision = _decision(decision_id)

    planner = ActionPlanningEngine()
    plan = planner.build(decision)

    approval_engine = ActionApprovalEngine()

    workflow = approval_engine.create(plan)

    workflow = approval_engine.approve(
        workflow,
        reviewer_id="ADMIN-1",
        decided_at=TEST_TIME,
        comment="Approved for controlled execution.",
    )

    return plan, workflow


def _gateway(calls):
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        lambda **kwargs: (
            calls.append(kwargs)
            or {"executed": True}
        ),
    )

    return gateway


def test_allowed_policy_reaches_execution_gateway():
    plan, workflow = _approved_plan()

    calls = []
    gateway = _gateway(calls)

    policy_engine = PolicyConstraintEngine(
        [
            PolicyConstraint(
                constraint_id="POL-ALLOW-HIGH",
                constraint_type="execution",
                description="High priority execution allowed.",
                allowed=True,
                priorities=("high",),
            )
        ]
    )

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.executed is True
    assert result.blocked is False
    assert result.execution is not None
    assert result.execution.status == "succeeded"
    assert len(calls) == 1


def test_blocked_policy_never_reaches_executor():
    plan, workflow = _approved_plan()

    calls = []
    gateway = _gateway(calls)

    policy_engine = PolicyConstraintEngine(
        [
            PolicyConstraint(
                constraint_id="POL-BLOCK-HIGH",
                constraint_type="execution",
                description="High priority execution blocked.",
                allowed=False,
                priorities=("high",),
            )
        ]
    )

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.blocked is True
    assert result.executed is False
    assert result.execution is None
    assert result.policy_check.status == "blocked"
    assert calls == []
    assert gateway.records == ()


def test_policy_check_is_preserved():
    plan, workflow = _approved_plan()

    gateway = _gateway([])

    policy_engine = PolicyConstraintEngine()

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.policy_check.plan_id == plan.plan_id
    assert result.policy_check.decision_id == plan.decision_id
    assert result.policy_check.status == "allowed"


def test_failed_constraint_ids_are_preserved():
    plan, workflow = _approved_plan()

    gateway = _gateway([])

    policy_engine = PolicyConstraintEngine(
        [
            PolicyConstraint(
                constraint_id="POL-BLOCK-1",
                constraint_type="execution",
                description="Execution is not permitted.",
                allowed=False,
                priorities=("high",),
            )
        ]
    )

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert "POL-BLOCK-1" in (
        result.policy_check.failed_constraint_ids
    )
    assert result.policy_check.failed_count == 1


def test_block_reason_contains_constraint_description():
    plan, workflow = _approved_plan()

    gateway = _gateway([])

    policy_engine = PolicyConstraintEngine(
        [
            PolicyConstraint(
                constraint_id="POL-BLOCK-REASON",
                constraint_type="execution",
                description="This action requires additional authorization.",
                allowed=False,
                priorities=("high",),
            )
        ]
    )

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert "additional authorization" in result.reason


def test_human_approval_remains_required_when_allowed():
    plan, workflow = _approved_plan()

    gateway = _gateway([])

    enforcer = ExecutionPolicyEnforcer(
        PolicyConstraintEngine(),
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.requires_human_approval is True


def test_human_approval_remains_required_when_blocked():
    plan, workflow = _approved_plan()

    gateway = _gateway([])

    policy_engine = PolicyConstraintEngine(
        [
            PolicyConstraint(
                constraint_id="POL-BLOCK-APPROVAL",
                constraint_type="execution",
                description="Policy blocks this action.",
                allowed=False,
                priorities=("high",),
            )
        ]
    )

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.requires_human_approval is True


def test_enforcer_rejects_invalid_plan():
    gateway = _gateway([])

    enforcer = ExecutionPolicyEnforcer(
        PolicyConstraintEngine(),
        ApprovalExecutionBridge(gateway),
    )

    with pytest.raises(TypeError):
        enforcer.check("not-a-plan")


def test_enforcer_rejects_invalid_workflow():
    plan, _ = _approved_plan()

    gateway = _gateway([])

    enforcer = ExecutionPolicyEnforcer(
        PolicyConstraintEngine(),
        ApprovalExecutionBridge(gateway),
    )

    with pytest.raises(TypeError):
        enforcer.execute(
            workflow="not-a-workflow",
            plan=plan,
            executor_name="test_executor",
            created_at=TEST_TIME,
        )


def test_allowed_execution_preserves_policy_metadata():
    plan, workflow = _approved_plan()

    gateway = _gateway([])

    policy_engine = PolicyConstraintEngine(
        [
            PolicyConstraint(
                constraint_id="POL-ALLOW-META",
                constraint_type="execution",
                description="Execution permitted.",
                allowed=True,
                priorities=("high",),
            )
        ]
    )

    enforcer = ExecutionPolicyEnforcer(
        policy_engine,
        ApprovalExecutionBridge(gateway),
    )

    result = enforcer.execute_approved(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.executed is True
    assert result.blocked is False
    assert result.metadata["policy_status"] == "allowed"
    assert result.metadata["workflow_id"] == workflow.workflow_id
    assert result.metadata["approval_id"] == (
        workflow.approval_history[-1].approval_id
    )
