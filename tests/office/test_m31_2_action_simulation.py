from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.action_simulation import (
    ActionSimulation,
    ActionSimulationEngine,
    SimulationOutcome,
    SimulationRisk,
)
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)


def make_plan():
    decision = DecisionIntelligence(
        decision_id="DINT-M31-2",
        decision_type="workload_review",
        created_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
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
                evidence_id="EVID-M31-2",
                evidence_type="current_signal",
                source_id="SIG-M31-2",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.8},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )

    return ActionPlanningEngine().build(decision)


def test_simulation_builds():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert isinstance(simulation, ActionSimulation)
    assert simulation.simulation_id == "SIM-APLAN-DINT-M31-2"
    assert simulation.plan_id == "APLAN-DINT-M31-2"
    assert simulation.decision_id == "DINT-M31-2"


def test_outcome_is_generated():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert simulation.outcome_count == 1

    outcome = simulation.outcomes[0]

    assert isinstance(outcome, SimulationOutcome)
    assert outcome.outcome_id == "SOUT-APLAN-DINT-M31-2-1"
    assert 0.0 <= outcome.probability <= 1.0
    assert 0.0 <= outcome.confidence <= 1.0


def test_risk_is_generated():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert simulation.risk_count == 1

    risk = simulation.risks[0]

    assert isinstance(risk, SimulationRisk)
    assert risk.risk_id == "SRISK-APLAN-DINT-M31-2-1"
    assert risk.severity == "high"
    assert 0.0 <= risk.probability <= 1.0


def test_evidence_is_preserved():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert simulation.evidence_ids == ("EVID-M31-2",)
    assert simulation.outcomes[0].evidence_ids == ("EVID-M31-2",)
    assert simulation.risks[0].evidence_ids == ("EVID-M31-2",)


def test_affected_entities_are_preserved():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert simulation.affected_user_ids == ("U1",)
    assert simulation.affected_system_ids == ("SYS1",)


def test_confidence_is_bounded():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert 0.0 <= simulation.confidence <= 1.0


def test_human_approval_is_required():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert simulation.requires_human_approval is True


def test_simulation_is_not_executable():
    simulation = ActionSimulationEngine().simulate(make_plan())

    assert simulation.executable is False
    assert not hasattr(simulation, "execute")
    assert not hasattr(ActionSimulationEngine, "execute")


def test_simulate_many():
    engine = ActionSimulationEngine()
    plans = (make_plan(),)

    simulations = engine.simulate_many(plans)

    assert len(simulations) == 1
    assert simulations[0].decision_id == "DINT-M31-2"


def test_invalid_plan_type():
    with pytest.raises(TypeError):
        ActionSimulationEngine().simulate(object())
