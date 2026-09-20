from datetime import datetime, timezone

import pytest

from yoma.office.action_planning import ActionPlanningEngine
from yoma.office.action_simulation import ActionSimulationEngine
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.what_if_intelligence import (
    WhatIfAlternative,
    WhatIfComparison,
    WhatIfIntelligenceEngine,
)


def make_decision():
    return DecisionIntelligence(
        decision_id="DINT-M31-3",
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
                evidence_id="EVID-M31-3",
                evidence_type="current_signal",
                source_id="SIG-M31-3",
                description="High workload detected.",
                weight=0.9,
                data={"score": 0.8},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload allocation.",
        requires_human_approval=True,
    )


def make_plan():
    return ActionPlanningEngine().build(make_decision())


def make_simulation():
    return ActionSimulationEngine().simulate(make_plan())


def test_compare_builds():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    assert isinstance(comparison, WhatIfComparison)
    assert comparison.comparison_id == "WIF-DINT-M31-3"
    assert comparison.decision_id == "DINT-M31-3"


def test_alternative_is_created():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    assert comparison.alternative_count == 1

    alternative = comparison.alternatives[0]

    assert isinstance(alternative, WhatIfAlternative)
    assert alternative.alternative_id == "WALT-APLAN-DINT-M31-3"
    assert alternative.plan_id == plan.plan_id
    assert alternative.simulation_id == simulation.simulation_id


def test_scores_are_bounded():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    alternative = comparison.alternatives[0]

    assert 0.0 <= alternative.expected_outcome_score <= 1.0
    assert 0.0 <= alternative.risk_score <= 1.0
    assert 0.0 <= alternative.confidence_score <= 1.0
    assert 0.0 <= alternative.impact_score <= 1.0
    assert 0.0 <= alternative.overall_score <= 1.0


def test_evidence_is_preserved():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    assert comparison.alternatives[0].evidence_ids == (
        "EVID-M31-3",
    )


def test_alternatives_are_ranked():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    assert comparison.preferred_alternative_id == (
        comparison.alternatives[0].alternative_id
    )


def test_multiple_alternatives():
    plan1 = make_plan()
    plan2 = make_plan()
    simulation1 = make_simulation()
    simulation2 = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan1, plan2),
        (simulation1, simulation2),
    )

    assert comparison.alternative_count == 2


def test_human_approval_required():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    assert comparison.requires_human_approval is True
    assert comparison.requires_review is True


def test_not_executable():
    plan = make_plan()
    simulation = make_simulation()

    comparison = WhatIfIntelligenceEngine().compare(
        "DINT-M31-3",
        (plan,),
        (simulation,),
    )

    assert comparison.executable is False
    assert not hasattr(comparison, "execute")
    assert not hasattr(WhatIfIntelligenceEngine, "execute")


def test_mismatched_simulation_rejected():
    plan = make_plan()
    simulation = ActionSimulationEngine().simulate(plan)

    bad_simulation = type(simulation)(
        simulation_id="SIM-OTHER",
        plan_id="APLAN-OTHER",
        decision_id="DINT-OTHER",
        outcomes=simulation.outcomes,
        risks=simulation.risks,
        confidence=simulation.confidence,
        affected_user_ids=simulation.affected_user_ids,
        affected_system_ids=simulation.affected_system_ids,
        evidence_ids=simulation.evidence_ids,
        requires_human_approval=True,
        metadata=simulation.metadata,
    )

    with pytest.raises(ValueError):
        WhatIfIntelligenceEngine().compare(
            "DINT-M31-3",
            (plan,),
            (bad_simulation,),
        )


def test_invalid_input_rejected():
    with pytest.raises(ValueError):
        WhatIfIntelligenceEngine().compare(
            "INVALID",
            (),
            (),
        )
