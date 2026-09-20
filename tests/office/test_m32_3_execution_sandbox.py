from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_execution import ActionExecutionGateway
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.execution_sandbox import ExecutionSandbox


TEST_TIME = datetime(2026, 9, 5, tzinfo=timezone.utc)


def _decision(
    decision_id: str = "DINT-M32-3",
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
    decision_id: str = "DINT-M32-3",
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
        comment="Approved for controlled review.",
    )

    return plan, workflow


def test_sandbox_requires_approved_workflow():
    plan, workflow = _approved_plan()

    pending = workflow.__class__(
        workflow_id=workflow.workflow_id + "-PENDING",
        plan_id=workflow.plan_id,
        decision_id=workflow.decision_id,
        status="pending",
        approval_history=(),
    )

    sandbox = ExecutionSandbox()

    with pytest.raises(PermissionError):
        sandbox.simulate(
            workflow=pending,
            plan=plan,
            executor_name="test_executor",
            created_at=TEST_TIME,
        )


def test_sandbox_simulates_without_real_executor():
    plan, workflow = _approved_plan()

    gateway = ActionExecutionGateway()
    calls = []

    gateway.register_executor(
        "dangerous_executor",
        lambda **kwargs: calls.append(kwargs),
    )

    sandbox = ExecutionSandbox()

    result = sandbox.simulate(
        workflow=workflow,
        plan=plan,
        executor_name="dangerous_executor",
        created_at=TEST_TIME,
    )

    assert result.simulated is True
    assert result.executable is False
    assert calls == []
    assert gateway.records == ()


def test_sandbox_result_is_marked_dry_run():
    plan, workflow = _approved_plan()

    result = ExecutionSandbox().dry_run(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert result.sandbox_execution.status == "simulated"
    assert result.sandbox_execution.simulated_output["dry_run"] is True
    assert result.sandbox_execution.simulated_output["side_effects"] is False


def test_sandbox_never_requires_registered_executor():
    plan, workflow = _approved_plan()

    result = ExecutionSandbox().simulate(
        workflow=workflow,
        plan=plan,
        executor_name="executor_that_does_not_exist",
        created_at=TEST_TIME,
    )

    assert result.execution_result.status == "succeeded"
    assert result.executable is False


def test_sandbox_preserves_approval_id():
    plan, workflow = _approved_plan()

    result = ExecutionSandbox().simulate(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    assert (
        result.sandbox_execution.approval_id
        == workflow.approval_history[-1].approval_id
    )


def test_sandbox_preserves_workflow_and_plan():
    plan, workflow = _approved_plan()

    result = ExecutionSandbox().simulate(
        workflow=workflow,
        plan=plan,
        executor_name="test_executor",
        created_at=TEST_TIME,
    )

    record = result.sandbox_execution

    assert record.workflow_id == workflow.workflow_id
    assert record.plan_id == plan.plan_id


def test_sandbox_rejects_mismatched_plan():
    plan, workflow = _approved_plan(
        "DINT-M32-3-A",
    )

    other_plan, _ = _approved_plan(
        "DINT-M32-3-B",
    )

    assert plan.plan_id != other_plan.plan_id

    sandbox = ExecutionSandbox()

    with pytest.raises(ValueError):
        sandbox.simulate(
            workflow=workflow,
            plan=other_plan,
            executor_name="test_executor",
            created_at=TEST_TIME,
        )


def test_sandbox_records_are_deterministically_sorted():
    plan, workflow = _approved_plan()

    sandbox = ExecutionSandbox()

    sandbox.simulate(
        workflow=workflow,
        plan=plan,
        executor_name="executor",
        created_at=TEST_TIME,
    )

    assert len(sandbox.records) == 1
    assert sandbox.records[0].sandbox_id.startswith("SANDBOX-")


def test_sandbox_does_not_create_real_execution_id():
    plan, workflow = _approved_plan()

    result = ExecutionSandbox().simulate(
        workflow=workflow,
        plan=plan,
        executor_name="executor",
        created_at=TEST_TIME,
    )

    assert result.sandbox_id.startswith("SANDBOX-")
    assert result.sandbox_id != (
        f"EXEC-{result.sandbox_execution.action_id}"
    )


def test_sandbox_output_explicitly_states_no_external_call():
    plan, workflow = _approved_plan()

    result = ExecutionSandbox().simulate(
        workflow=workflow,
        plan=plan,
        executor_name="executor",
        created_at=TEST_TIME,
    )

    output = result.sandbox_execution.simulated_output

    assert output["external_system_called"] is False
    assert output["human_approval_verified"] is True
    assert output["simulated"] is True
