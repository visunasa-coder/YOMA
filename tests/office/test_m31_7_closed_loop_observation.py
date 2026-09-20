from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.closed_loop_observation import (
    ClosedLoopObservation,
    ClosedLoopObservationEngine,
    OperationalObservation,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def make_workflow():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-7",
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
                evidence_id="EVID-M31-7",
                evidence_type="current_signal",
                source_id="SIG-M31-7",
                description="High workload detected.",
                weight=0.9,
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )

    plan = ActionPlanningEngine().build(decision)

    engine = ActionApprovalEngine()
    workflow = engine.create(plan)

    return engine.approve(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
        comment="Approved.",
    )


def test_create_closed_loop():
    workflow = make_workflow()

    loop = ClosedLoopObservationEngine().create(
        workflow,
        expected_event_count=2,
    )

    assert isinstance(loop, ClosedLoopObservation)
    assert loop.observation_id == (
        "CLOOP-AWF-APLAN-DINT-M31-7"
    )
    assert loop.workflow_id == workflow.workflow_id
    assert loop.plan_id == workflow.plan_id
    assert loop.decision_id == workflow.decision_id
    assert loop.outcome_status == "pending"


def test_record_observation():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow(), expected_event_count=1)

    updated = engine.record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Workload was redistributed.",
        event_ids=("EV-1",),
        affected_user_ids=("U1",),
        affected_system_ids=("SYS1",),
        evidence={"result": "success"},
    )

    assert updated.observation_count == 1
    assert updated.observed_event_count == 1
    assert updated.outcome_status == "observed"


def test_observation_details_preserved():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow())

    updated = engine.record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Observed operational response.",
        event_ids=("EV-1", "EV-2"),
        affected_user_ids=("U2", "U1"),
        affected_system_ids=("SYS2",),
        evidence={"metric": 0.8},
    )

    observation = updated.observations[0]

    assert isinstance(observation, OperationalObservation)
    assert observation.observation_id == (
        "OBS-CLOOP-AWF-APLAN-DINT-M31-7-1"
    )
    assert observation.event_ids == ("EV-1", "EV-2")
    assert observation.affected_user_ids == ("U1", "U2")
    assert observation.affected_system_ids == ("SYS2",)
    assert observation.evidence["metric"] == 0.8


def test_expectation_matches():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow(), expected_event_count=2)

    updated = engine.record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Expected events observed.",
        event_ids=("EV-1", "EV-2"),
    )

    assert updated.complete is True
    assert updated.matches_expectation is True


def test_partial_observation():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow(), expected_event_count=3)

    updated = engine.record(
        loop,
        observed_at=NOW,
        outcome_status="partial",
        description="Only part of the expected response occurred.",
        event_ids=("EV-1",),
    )

    assert updated.complete is True
    assert updated.outcome_status == "partial"
    assert updated.matches_expectation is False


def test_failed_observation():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow())

    updated = engine.record(
        loop,
        observed_at=NOW,
        outcome_status="failed",
        description="Expected operational response was not observed.",
    )

    assert updated.complete is True
    assert updated.outcome_status == "failed"


def test_human_approval_required():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow())

    assert loop.requires_human_approval is True
    assert loop.requires_review is True


def test_observation_is_not_execution():
    engine = ClosedLoopObservationEngine()
    loop = engine.create(make_workflow())

    assert loop.executable is False
    assert not hasattr(loop, "execute")
    assert not hasattr(engine, "execute")


def test_unapproved_workflow_rejected():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-7B",
        decision_type="test",
        created_at=NOW,
        priority="normal",
        confidence=0.5,
        recommendation_type="test",
        recommendation_reason="Test.",
        requires_human_approval=True,
    )

    plan = ActionPlanningEngine().build(decision)
    workflow = ActionApprovalEngine().create(plan)

    with pytest.raises(ValueError):
        ClosedLoopObservationEngine().create(workflow)


def test_invalid_input():
    with pytest.raises(TypeError):
        ClosedLoopObservationEngine().create(object())
