from datetime import datetime, timezone

import pytest

from yoma.office.action_approval import ActionApprovalEngine
from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.action_simulation import ActionSimulationEngine
from yoma.office.closed_loop_observation import (
    ClosedLoopObservationEngine,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.outcome_learning import (
    OutcomeLearningEngine,
    OutcomeLearningResult,
    OutcomeLearningSignal,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def make_simulation_and_loop():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-8",
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
                evidence_id="EVID-M31-8",
                evidence_type="current_signal",
                source_id="SIG-M31-8",
                description="High workload detected.",
                weight=0.9,
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )

    plan = ActionPlanningEngine().build(decision)
    simulation = ActionSimulationEngine().simulate(plan)

    workflow = ActionApprovalEngine().create(plan)
    workflow = ActionApprovalEngine().approve(
        workflow,
        reviewer_id="MANAGER-1",
        decided_at=NOW,
    )

    loop = ClosedLoopObservationEngine().create(
        workflow,
        expected_event_count=1,
    )

    return simulation, loop


def test_outcome_learning_builds():
    simulation, loop = make_simulation_and_loop()

    loop = ClosedLoopObservationEngine().record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Expected workload response observed.",
        event_ids=("EV-M31-8",),
    )

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert isinstance(result, OutcomeLearningResult)
    assert result.result_id == "OLRN-SIM-APLAN-DINT-M31-8"
    assert result.decision_id == "DINT-M31-8"
    assert result.plan_id == "APLAN-DINT-M31-8"


def test_learning_signal_created():
    simulation, loop = make_simulation_and_loop()

    loop = ClosedLoopObservationEngine().record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Expected response observed.",
        event_ids=("EV-M31-8",),
    )

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert result.signal_count == 1

    signal = result.signals[0]

    assert isinstance(signal, OutcomeLearningSignal)
    assert signal.learning_id == (
        "LEARN-SIM-APLAN-DINT-M31-8"
    )


def test_accuracy_is_bounded():
    simulation, loop = make_simulation_and_loop()

    loop = ClosedLoopObservationEngine().record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Observed.",
        event_ids=("EV-1",),
    )

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert 0.0 <= result.prediction_accuracy <= 1.0
    assert 0.0 <= result.prediction_error <= 1.0


def test_error_is_inverse_of_accuracy():
    simulation, loop = make_simulation_and_loop()

    loop = ClosedLoopObservationEngine().record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Observed.",
        event_ids=("EV-1",),
    )

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert result.prediction_error == round(
        1.0 - result.prediction_accuracy,
        6,
    )


def test_evidence_is_combined():
    simulation, loop = make_simulation_and_loop()

    loop = ClosedLoopObservationEngine().record(
        loop,
        observed_at=NOW,
        outcome_status="observed",
        description="Observed.",
        event_ids=("EV-M31-8",),
    )

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert "EVID-M31-8" in result.signals[0].evidence_ids
    assert "EV-M31-8" in result.signals[0].evidence_ids


def test_insufficient_data():
    simulation, loop = make_simulation_and_loop()

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert result.prediction_outcome == "insufficient_data"
    assert result.signals[0].learning_direction == (
        "insufficient_data"
    )


def test_human_approval_required():
    simulation, loop = make_simulation_and_loop()

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert result.requires_human_approval is True
    assert result.requires_review is True


def test_learning_is_not_execution():
    simulation, loop = make_simulation_and_loop()

    result = OutcomeLearningEngine().learn(
        simulation,
        loop,
    )

    assert result.executable is False
    assert not hasattr(result, "execute")
    assert not hasattr(OutcomeLearningEngine, "execute")


def test_mismatched_plan_rejected():
    simulation, loop = make_simulation_and_loop()

    bad_loop = type(loop)(
        observation_id=loop.observation_id,
        workflow_id=loop.workflow_id,
        plan_id="APLAN-OTHER",
        decision_id=loop.decision_id,
        approval_status=loop.approval_status,
        observations=loop.observations,
        expected_event_count=loop.expected_event_count,
        observed_event_count=loop.observed_event_count,
        outcome_status=loop.outcome_status,
        requires_human_approval=True,
        metadata=loop.metadata,
    )

    with pytest.raises(ValueError):
        OutcomeLearningEngine().learn(
            simulation,
            bad_loop,
        )


def test_invalid_input():
    with pytest.raises(TypeError):
        OutcomeLearningEngine().learn(
            object(),
            object(),
        )
