from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_execution import ActionExecutionGateway
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.approval_execution_bridge import (
    ApprovalExecutionBridge,
    GovernedExecutionResult,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


NOW = datetime(
    2026,
    9,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_decision(decision_id="DINT-M32-2"):
    return DecisionIntelligence(
        decision_id=decision_id,
        decision_type="workload_review",
        created_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        current_decision_ids=("DEC-M32-2",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-M32-2",
                evidence_type="current_signal",
                source_id="SIG-M32-2",
                description="High workload detected.",
                weight=0.9,
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )


def make_plan():
    return ActionPlanningEngine().build(
        make_decision()
    )


def make_approved_workflow():
    plan = make_plan()

    engine = ActionApprovalEngine()

    workflow = engine.create(plan)

    workflow = engine.approve(
        workflow,
        reviewer_id="MANAGER-M32-2",
        decided_at=NOW,
        comment="Approved.",
    )

    return plan, workflow


def make_pending_workflow():
    plan = make_plan()

    workflow = ActionApprovalEngine().create(
        plan
    )

    return plan, workflow


def make_gateway():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        lambda **kwargs: {
            "executed": True,
            "action_id": kwargs["action_id"],
        },
    )

    return gateway


def test_bridge_requires_gateway():
    with pytest.raises(TypeError):
        ApprovalExecutionBridge(None)


def test_pending_workflow_cannot_execute():
    plan, workflow = make_pending_workflow()

    bridge = ApprovalExecutionBridge(
        make_gateway()
    )

    with pytest.raises(PermissionError):
        bridge.execute_approved(
            workflow,
            plan,
            executor_name="test_executor",
            created_at=NOW,
        )


def test_approved_workflow_executes():
    plan, workflow = make_approved_workflow()

    bridge = ApprovalExecutionBridge(
        make_gateway()
    )

    result = bridge.execute_approved(
        workflow,
        plan,
        executor_name="test_executor",
        created_at=NOW,
    )

    assert isinstance(
        result,
        GovernedExecutionResult,
    )

    assert result.status == "succeeded"
    assert result.approved is True
    assert result.executable is True


def test_execution_links_to_workflow():
    plan, workflow = make_approved_workflow()

    bridge = ApprovalExecutionBridge(
        make_gateway()
    )

    result = bridge.execute_approved(
        workflow,
        plan,
        executor_name="test_executor",
        created_at=NOW,
    )

    assert result.workflow_id == workflow.workflow_id
    assert result.approval_id == (
        workflow.approval_history[-1].approval_id
    )


def test_execution_record_matches_action():
    plan, workflow = make_approved_workflow()

    gateway = make_gateway()
    bridge = ApprovalExecutionBridge(gateway)

    result = bridge.execute_approved(
        workflow,
        plan,
        executor_name="test_executor",
        created_at=NOW,
    )

    record = gateway.get_record(
        result.execution_id
    )

    assert record is not None
    assert record.action_id == plan.steps[0].step_id
    assert record.action_type == plan.steps[0].action_type
    assert record.status == "succeeded"


def test_rejected_workflow_cannot_execute():
    plan = make_plan()

    engine = ActionApprovalEngine()

    workflow = engine.create(plan)

    workflow = engine.reject(
        workflow,
        reviewer_id="MANAGER-M32-2",
        decided_at=NOW,
        comment="Rejected.",
    )

    bridge = ApprovalExecutionBridge(
        make_gateway()
    )

    with pytest.raises(PermissionError):
        bridge.execute_approved(
            workflow,
            plan,
            executor_name="test_executor",
            created_at=NOW,
        )


def test_execution_failure_stays_inside_gateway():
    plan, workflow = make_approved_workflow()

    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "failing_executor",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("executor failed")
        ),
    )

    bridge = ApprovalExecutionBridge(gateway)

    result = bridge.execute_approved(
        workflow,
        plan,
        executor_name="failing_executor",
        created_at=NOW,
    )

    assert result.status == "failed"
    assert "executor failed" in result.execution.error


def test_bridge_does_not_bypass_gateway():
    plan, workflow = make_approved_workflow()

    gateway = make_gateway()
    bridge = ApprovalExecutionBridge(gateway)

    result = bridge.execute(
        workflow,
        plan,
        executor_name="test_executor",
        created_at=NOW,
    )

    assert result.execution_id in {
        record.execution_id
        for record in gateway.records
    }


def test_human_approval_is_preserved():
    plan, workflow = make_approved_workflow()

    bridge = ApprovalExecutionBridge(
        make_gateway()
    )

    result = bridge.execute_approved(
        workflow,
        plan,
        executor_name="test_executor",
        created_at=NOW,
    )

    assert workflow.requires_human_approval is True
    assert result.requires_human_approval is True
    assert result.execution.requires_human_approval is True


def test_plan_workflow_mismatch_is_blocked():
    plan, workflow = make_approved_workflow()

    other_plan = ActionPlanningEngine().build(
        make_decision(
            "DINT-M32-2-OTHER"
        )
    )

    bridge = ApprovalExecutionBridge(
        make_gateway()
    )

    with pytest.raises(ValueError):
        bridge.execute_approved(
            workflow,
            other_plan,
            executor_name="test_executor",
            created_at=NOW,
        )
