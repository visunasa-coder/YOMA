from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_planning import (
    ActionPlan,
    ActionPlanStep,
)

from yoma.office.distributed_organization_identity import (
    DistributedOrganizationIdentity,
    DistributedNodeIdentity,
)

from yoma.office.distributed_central_governance import (
    CentralGovernanceRequest,
    DistributedCentralGovernance,
)


NOW = datetime(
    2026,
    9,
    6,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_org():
    return DistributedOrganizationIdentity(
        organization_id="ORG-M45",
        organization_name="M45 Pilot",
        deployment_id="DEP-M45",
    )


def make_node():
    return DistributedNodeIdentity(
        node_id="NODE-PC-01",
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_name="Employee PC 01",
    )


def make_plan():
    return ActionPlan(
        plan_id="APLAN-M45-6",
        decision_id="DINT-M45-6",
        created_at=NOW,
        decision_type="operational_review",
        priority="high",
        reason="Review distributed operational condition.",
        steps=(
            ActionPlanStep(
                step_id="STEP-M45-6",
                sequence=1,
                action_type="review",
                description="Review proposed operational action.",
                parameters={},
            ),
        ),
        affected_system_ids=("yoma",),
        requires_human_approval=True,
    )


def make_request(request_id="REQ-M45-6"):
    return CentralGovernanceRequest(
        request_id=request_id,
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
        plan=make_plan(),
        requested_at=NOW,
    )


def make_runtime():
    return DistributedCentralGovernance(
        organization=make_org(),
        node=make_node(),
    )


def test_request_requires_action_plan():
    with pytest.raises(TypeError):
        CentralGovernanceRequest(
            request_id="REQ-1",
            organization_id="ORG-M45",
            deployment_id="DEP-M45",
            node_id="NODE-PC-01",
            plan="invalid",
            requested_at=NOW,
        )


def test_runtime_rejects_wrong_node_organization():
    with pytest.raises(ValueError):
        DistributedCentralGovernance(
            organization=make_org(),
            node=DistributedNodeIdentity(
                node_id="NODE-WRONG",
                organization_id="ORG-OTHER",
                deployment_id="DEP-M45",
                node_name="Wrong",
            ),
        )


def test_valid_request_passes_governance_validation():
    runtime = make_runtime()

    issues = runtime.validate_request(
        make_request()
    )

    assert issues == ()


def test_wrong_organization_is_rejected():
    runtime = make_runtime()

    request = CentralGovernanceRequest(
        request_id="REQ-WRONG-ORG",
        organization_id="ORG-OTHER",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
        plan=make_plan(),
        requested_at=NOW,
    )

    result = runtime.submit(request)

    assert result.governance_status == "rejected_by_governance"
    assert "organization_id mismatch" in result.validation_issues
    assert result.executable is False
    assert result.execution_allowed is False


def test_wrong_deployment_is_rejected():
    runtime = make_runtime()

    request = CentralGovernanceRequest(
        request_id="REQ-WRONG-DEP",
        organization_id="ORG-M45",
        deployment_id="DEP-OTHER",
        node_id="NODE-PC-01",
        plan=make_plan(),
        requested_at=NOW,
    )

    result = runtime.submit(request)

    assert result.governance_status == "rejected_by_governance"
    assert "deployment_id mismatch" in result.validation_issues


def test_wrong_node_is_rejected():
    runtime = make_runtime()

    request = CentralGovernanceRequest(
        request_id="REQ-WRONG-NODE",
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-OTHER",
        plan=make_plan(),
        requested_at=NOW,
    )

    result = runtime.submit(request)

    assert result.governance_status == "rejected_by_governance"
    assert "node_id mismatch" in result.validation_issues


def test_valid_request_creates_existing_approval_workflow():
    runtime = make_runtime()

    result = runtime.submit(
        make_request()
    )

    assert result.governance_status == "approved_for_review"
    assert result.workflow.status == "pending"
    assert result.workflow.plan_id == "APLAN-M45-6"
    assert result.workflow.decision_id == "DINT-M45-6"


def test_human_approval_is_required():
    runtime = make_runtime()

    result = runtime.submit(
        make_request()
    )

    assert result.requires_human_approval is True
    assert result.approval_pending is True


def test_governance_never_becomes_executable():
    runtime = make_runtime()

    result = runtime.submit(
        make_request()
    )

    assert result.executable is False
    assert result.execution_allowed is False
    assert runtime.executable is False
    assert runtime.execution_allowed is False


def test_duplicate_request_is_idempotent():
    runtime = make_runtime()

    first = runtime.submit(
        make_request("REQ-DUP")
    )

    second = runtime.submit(
        make_request("REQ-DUP")
    )

    assert second is first
    assert len(runtime.requests) == 1
    assert len(runtime.results) == 1


def test_explicit_human_approval_is_recorded():
    runtime = make_runtime()

    result = runtime.submit(
        make_request("REQ-APPROVE")
    )

    approved = runtime.approve(
        "REQ-APPROVE",
        reviewer_id="MANAGER-01",
        decided_at=NOW,
        comment="Approved for review.",
    )

    assert approved.workflow.status == "approved"
    assert approved.approved is True
    assert approved.executable is False
    assert approved.execution_allowed is False
    assert approved.requires_human_approval is True


def test_explicit_human_rejection_is_recorded():
    runtime = make_runtime()

    runtime.submit(
        make_request("REQ-REJECT")
    )

    rejected = runtime.reject(
        "REQ-REJECT",
        reviewer_id="MANAGER-01",
        decided_at=NOW,
        comment="Rejected.",
    )

    assert rejected.workflow.status == "rejected"
    assert rejected.rejected is True
    assert rejected.executable is False
    assert rejected.execution_allowed is False


def test_explicit_human_modification_is_recorded():
    runtime = make_runtime()

    runtime.submit(
        make_request("REQ-MODIFY")
    )

    modified = runtime.modify(
        "REQ-MODIFY",
        reviewer_id="MANAGER-01",
        decided_at=NOW,
        modifications={"priority": "medium"},
        comment="Reduce priority.",
    )

    assert modified.workflow.status == "modified"
    assert modified.modified is True
    assert modified.executable is False
    assert modified.execution_allowed is False


def test_unknown_request_cannot_be_approved():
    runtime = make_runtime()

    with pytest.raises(KeyError):
        runtime.approve(
            "REQ-UNKNOWN",
            reviewer_id="MANAGER-01",
            decided_at=NOW,
        )


def test_unknown_request_cannot_be_rejected():
    runtime = make_runtime()

    with pytest.raises(KeyError):
        runtime.reject(
            "REQ-UNKNOWN",
            reviewer_id="MANAGER-01",
            decided_at=NOW,
        )


def test_naive_approval_timestamp_is_rejected():
    runtime = make_runtime()

    runtime.submit(
        make_request("REQ-TZ")
    )

    with pytest.raises(ValueError):
        runtime.approve(
            "REQ-TZ",
            reviewer_id="MANAGER-01",
            decided_at=datetime(2026, 9, 6, 12, 0),
        )


def test_custom_approval_engine_is_reused():
    engine = ActionApprovalEngine()

    runtime = DistributedCentralGovernance(
        organization=make_org(),
        node=make_node(),
        approval_engine=engine,
    )

    assert runtime.approval_engine is engine


def test_get_returns_current_result():
    runtime = make_runtime()

    submitted = runtime.submit(
        make_request("REQ-GET")
    )

    assert runtime.get("REQ-GET") is submitted


def test_get_unknown_request_returns_none():
    runtime = make_runtime()

    assert runtime.get("DOES-NOT-EXIST") is None


def test_request_metadata_is_preserved():
    runtime = make_runtime()

    request = CentralGovernanceRequest(
        request_id="REQ-META",
        organization_id="ORG-M45",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
        plan=make_plan(),
        requested_at=NOW,
        metadata={"source": "employee_pc"},
    )

    result = runtime.submit(request)

    assert result.metadata["source"] == "employee_pc"
    assert result.metadata["source"] == "employee_pc"


def test_rejected_governance_result_cannot_execute():
    runtime = make_runtime()

    request = CentralGovernanceRequest(
        request_id="REQ-SAFE",
        organization_id="ORG-OTHER",
        deployment_id="DEP-M45",
        node_id="NODE-PC-01",
        plan=make_plan(),
        requested_at=NOW,
    )

    result = runtime.submit(request)

    assert result.rejected is False
    assert result.governance_status == "rejected_by_governance"
    assert result.executable is False
    assert result.execution_allowed is False


def test_runtime_requires_human_approval():
    runtime = make_runtime()

    assert runtime.requires_human_approval is True
