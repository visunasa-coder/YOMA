from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import (
    ActionApprovalEngine,
    ActionApprovalWorkflow,
    ApprovalRecord,
)
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def make_plan():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-6",
        decision_type="workload_review",
        created_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        system_id="SYS1",
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        current_decision_ids=("DEC-1",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-M31-6",
                evidence_type="current_signal",
                source_id="SIG-M31-6",
                description="High workload detected.",
                weight=0.9,
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )

    return ActionPlanningEngine().build(decision)


def test_create_pending_workflow():
    workflow = ActionApprovalEngine().create(make_plan())

    assert isinstance(workflow, ActionApprovalWorkflow)
    assert workflow.workflow_id == "AWF-APLAN-DINT-M31-6"
    assert workflow.plan_id == "APLAN-DINT-M31-6"
    assert workflow.decision_id == "DINT-M31-6"
    assert workflow.status == "pending"
    assert workflow.pending is True


def test_approve():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    approved = engine.approve(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
        comment="Approved after review.",
    )

    assert approved.approved is True
    assert approved.status == "approved"
    assert approved.review_count == 1
    assert approved.approval_history[0].reviewer_id == "MANAGER-1"


def test_reject():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    rejected = engine.reject(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
        comment="Risk too high.",
    )

    assert rejected.rejected is True
    assert rejected.status == "rejected"


def test_modify():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    modified = engine.modify(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
        modifications={
            "target_user_id": "U2",
            "reason": "Redistribute workload.",
        },
        comment="Modified target.",
    )

    assert modified.modified is True
    assert modified.status == "modified"
    assert modified.approval_history[0].modifications["target_user_id"] == "U2"


def test_approval_record_is_created():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    approved = engine.approve(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
    )

    record = approved.approval_history[0]

    assert isinstance(record, ApprovalRecord)
    assert record.approval_id == "APP-AWF-APLAN-DINT-M31-6-1"
    assert record.plan_id == workflow.plan_id
    assert record.decision_id == workflow.decision_id


def test_only_pending_can_be_decided():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    approved = engine.approve(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
    )

    with pytest.raises(ValueError):
        engine.reject(
            approved,
            reviewer_id="MANAGER-2",
            decided_at=NOW,
        )


def test_empty_reviewer_rejected():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    with pytest.raises(ValueError):
        engine.approve(
            workflow,
            reviewer_id="",
            decided_at=NOW,
        )


def test_empty_modification_rejected():
    engine = ActionApprovalEngine()
    workflow = engine.create(make_plan())

    with pytest.raises(ValueError):
        engine.modify(
            workflow,
            reviewer_id="MANAGER-1",
            decided_at=NOW,
            modifications={},
        )


def test_human_approval_is_required():
    workflow = ActionApprovalEngine().create(make_plan())

    assert workflow.requires_human_approval is True


def test_no_execution_capability():
    workflow = ActionApprovalEngine().create(make_plan())

    assert workflow.executable is False
    assert not hasattr(workflow, "execute")
    assert not hasattr(ActionApprovalEngine, "execute")
