from datetime import datetime, timezone

import pytest

from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.decision_evidence_graph import (
    DecisionEvidenceGraphBuilder,
)
from yoma.office.decision_explanation import (
    DecisionExplanation,
    DecisionExplanationEngine,
)
from yoma.office.decision_priority import DecisionPriorityScore


def make_decision(**overrides):
    values = dict(
        decision_id="DINT-001",
        decision_type="operational_review",
        created_at=datetime.now(timezone.utc),
        organization_id="ORG-1",
        user_id="USR-1",
        system_id=None,
        situation_type="workload.high",
        priority="high",
        confidence=0.80,
        current_intelligence_available=True,
        historical_intelligence_available=True,
        predictive_intelligence_available=True,
        current_decision_ids=("DEC-1",),
        historical_context_ids=("HIST-1",),
        predictive_context_ids=("PRED-1",),
        evidence=(
            DecisionIntelligenceEvidence(
                evidence_id="EVID-1",
                evidence_type="predictive",
                source_id="PRED-1",
                description="Forecast supports elevated workload risk.",
                weight=0.80,
                data={"probability": 0.80},
            ),
        ),
        recommendation_type="workload_review",
        recommendation_reason="Review workload before the predicted pressure window.",
        requires_human_approval=True,
    )
    values.update(overrides)
    return DecisionIntelligence(**values)


def make_graph(decision):
    return DecisionEvidenceGraphBuilder().build(decision)


def make_score(decision_id="DINT-001"):
    return DecisionPriorityScore(
        decision_id=decision_id,
        priority="high",
        priority_score=0.75,
        confidence_score=0.80,
        intelligence_score=1.0,
        evidence_score=0.68,
        urgency_score=1.0,
        total_score=0.82,
        rank=1,
    )


def test_explanation_model_defaults():
    explanation = DecisionExplanation(
        explanation_id="DEXP-DINT-001",
        decision_id="DINT-001",
        summary="Summary",
        why_it_matters="Reason",
    )

    assert explanation.priority == "normal"
    assert explanation.confidence == 0.0
    assert explanation.requires_human_approval is True
    assert explanation.evidence_count == 0
    assert explanation.context_count == 0
    assert explanation.explainable is False


def test_explanation_uncertainty_levels():
    engine = DecisionExplanationEngine()

    for confidence, expected in (
        (0.90, "low"),
        (0.70, "moderate"),
        (0.40, "high"),
    ):
        decision = make_decision(confidence=confidence)
        result = engine.explain(decision, make_graph(decision))
        assert result.uncertainty_level == expected


def test_explanation_contains_current_context():
    decision = make_decision()
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.current_context == ("DEC-1",)


def test_explanation_contains_historical_context():
    decision = make_decision()
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.historical_context == ("HIST-1",)


def test_explanation_contains_predictive_context():
    decision = make_decision()
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.predictive_context == ("PRED-1",)


def test_explanation_contains_evidence():
    decision = make_decision()
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.evidence_count == 1
    assert "EVID-1" in result.supporting_evidence[0]


def test_explanation_is_deterministic():
    decision = make_decision()
    engine = DecisionExplanationEngine()

    first = engine.explain(decision, make_graph(decision))
    second = engine.explain(decision, make_graph(decision))

    assert first == second


def test_explanation_uses_priority_score():
    decision = make_decision()
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
        make_score(),
    )

    assert result.priority == "high"
    assert result.priority_score == 0.82


def test_explanation_preserves_recommendation():
    decision = make_decision()
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.recommendation == (
        "Review workload before the predicted pressure window."
    )


def test_low_confidence_is_explicit_uncertainty():
    decision = make_decision(
        confidence=0.45,
        historical_intelligence_available=False,
        predictive_intelligence_available=False,
        historical_context_ids=(),
        predictive_context_ids=(),
    )

    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert "Decision confidence is below 0.60." in result.uncertainty
    assert "No historical context is attached to this decision." in result.uncertainty
    assert "No predictive context is attached to this decision." in result.uncertainty


def test_no_evidence_is_explicit():
    decision = make_decision(evidence=())
    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.explainable is False
    assert result.evidence_count == 1
    assert "No explicit evidence nodes" in result.supporting_evidence[0]


def test_graph_decision_mismatch_rejected():
    decision = make_decision()
    graph = make_graph(make_decision(decision_id="DINT-OTHER"))

    with pytest.raises(ValueError, match="graph.decision_id"):
        DecisionExplanationEngine().explain(decision, graph)


def test_invalid_decision_rejected():
    with pytest.raises(TypeError, match="decision"):
        DecisionExplanationEngine().explain(
            object(),
            object(),
        )


def test_invalid_graph_rejected():
    decision = make_decision()

    with pytest.raises(TypeError, match="graph"):
        DecisionExplanationEngine().explain(
            decision,
            object(),
        )


def test_priority_score_mismatch_rejected():
    decision = make_decision()

    with pytest.raises(ValueError, match="priority_score.decision_id"):
        DecisionExplanationEngine().explain(
            decision,
            make_graph(decision),
            make_score("DINT-OTHER"),
        )


def test_explain_many_is_sorted():
    engine = DecisionExplanationEngine()

    decision_b = make_decision(decision_id="DINT-B")
    decision_a = make_decision(decision_id="DINT-A")

    results = engine.explain_many(
        [decision_b, decision_a],
        [make_graph(decision_b), make_graph(decision_a)],
    )

    assert [item.decision_id for item in results] == [
        "DINT-A",
        "DINT-B",
    ]


def test_explain_many_uses_priority_scores():
    engine = DecisionExplanationEngine()
    decision = make_decision()

    results = engine.explain_many(
        [decision],
        [make_graph(decision)],
        [make_score()],
    )

    assert results[0].priority_score == 0.82


def test_explain_many_missing_graph_rejected():
    decision = make_decision()

    with pytest.raises(ValueError, match="No evidence graph"):
        DecisionExplanationEngine().explain_many(
            [decision],
            [],
        )


def test_explanation_requires_human_approval():
    decision = make_decision()

    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.requires_human_approval is True


def test_explanation_id_is_deterministic():
    decision = make_decision()

    result = DecisionExplanationEngine().explain(
        decision,
        make_graph(decision),
    )

    assert result.explanation_id == "DEXP-DINT-001"
