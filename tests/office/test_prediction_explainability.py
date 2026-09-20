from datetime import datetime, timedelta

import pytest

from yoma.office.predictive_decision_context import (
    PredictiveDecisionContextBuilder,
)
from yoma.office.predictive_situation import PredictiveSituation
from yoma.office.prediction_explainability import (
    PredictionExplainability,
    PredictionExplainabilityEngine,
    PredictionFactor,
)


BASE = datetime(2026, 9, 1, 10, 0, 0)
NEXT = BASE + timedelta(days=7)


def make_situation(
    probability=0.75,
    confidence=0.80,
    severity="high",
):
    return PredictiveSituation(
        prediction_id="PSIT-PRED-S1",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        predicted_at=BASE,
        forecast_start=NEXT,
        forecast_end=NEXT + timedelta(hours=2),
        probability=probability,
        confidence=confidence,
        severity=severity,
        prediction_sources=(
            "predictive_signal",
            "risk_forecast",
            "recurrence_prediction",
            "workload_forecast",
        ),
        evidence_situation_ids=("S1", "S2", "S3"),
        evidence=("prediction evidence",),
    )


def make_context():
    return PredictiveDecisionContextBuilder().build(
        make_situation()
    )


def test_factor_validates_contribution():
    with pytest.raises(ValueError):
        PredictionFactor(
            factor_type="test",
            name="test",
            value="test",
            contribution=-0.1,
            evidence="test",
        )

    with pytest.raises(ValueError):
        PredictionFactor(
            factor_type="test",
            name="test",
            value="test",
            contribution=1.1,
            evidence="test",
        )


def test_explainability_dataclass_is_valid():
    result = PredictionExplainability(
        explanation_id="EXPL-P1",
        prediction_id="P1",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        confidence=0.8,
        evidence_strength=0.9,
        uncertainty=0.2,
        confidence_level="high",
        evidence_level="strong",
        factors=(
            PredictionFactor(
                factor_type="historical",
                name="history",
                value="3",
                contribution=0.8,
                evidence="history",
            ),
        ),
        evidence_situation_ids=("S1",),
        explanation="Explanation.",
        limitations=("Limitation.",),
    )

    assert result.explainable is True
    assert result.uncertainty_level == "low"
    assert result.requires_human_approval is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("confidence", -0.1),
        ("confidence", 1.1),
        ("evidence_strength", -0.1),
        ("evidence_strength", 1.1),
        ("uncertainty", -0.1),
        ("uncertainty", 1.1),
    ],
)
def test_explainability_values_are_bounded(field, value):
    kwargs = dict(
        explanation_id="E1",
        prediction_id="P1",
        situation_type="x",
        organization_id=None,
        user_id=None,
        system_id=None,
        confidence=0.5,
        evidence_strength=0.5,
        uncertainty=0.5,
        confidence_level="moderate",
        evidence_level="moderate",
        factors=(),
        evidence_situation_ids=(),
        explanation="x",
        limitations=(),
    )

    kwargs[field] = value

    with pytest.raises(ValueError):
        PredictionExplainability(**kwargs)


def test_engine_generates_explanation():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert result.prediction_id == "PSIT-PRED-S1"
    assert result.situation_type == "workload_pressure"
    assert result.confidence == 0.80
    assert result.confidence_level == "high"
    assert result.evidence_strength > 0.75
    assert result.evidence_level == "strong"
    assert result.explainable is True


def test_all_predictive_sources_become_factors():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    factor_types = {
        factor.factor_type
        for factor in result.factors
    }

    assert "probability" in factor_types
    assert "confidence" in factor_types
    assert "historical" in factor_types
    assert "risk" in factor_types
    assert "recurrence" in factor_types
    assert "workload" in factor_types


def test_explanation_contains_probability_and_confidence():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert "probability 0.75" in result.explanation
    assert "confidence 0.80" in result.explanation
    assert "workload_pressure" in result.explanation
    assert "human review" in result.explanation


def test_evidence_ids_are_preserved():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert result.evidence_situation_ids == (
        "S1",
        "S2",
        "S3",
    )


def test_limitations_are_explicit():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert len(result.limitations) >= 3
    assert any(
        "probabilistic" in item
        for item in result.limitations
    )
    assert any(
        "autonomous action" in item
        for item in result.limitations
    )


def test_low_confidence_adds_extra_limitation():
    context = PredictiveDecisionContextBuilder().build(
        make_situation(
            probability=0.40,
            confidence=0.30,
            severity="warning",
        )
    )

    result = PredictionExplainabilityEngine().explain(
        context
    )

    assert result.confidence_level == "low"
    assert any(
        "low" in item.lower()
        for item in result.limitations
    )


def test_single_source_is_flagged_as_limited():
    signal_only = PredictiveSituation(
        prediction_id="PSIT-SINGLE",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        predicted_at=BASE,
        forecast_start=NEXT,
        forecast_end=NEXT + timedelta(hours=1),
        probability=0.70,
        confidence=0.80,
        severity="high",
        prediction_sources=("predictive_signal",),
        evidence_situation_ids=("S1",),
        evidence=("signal",),
    )

    context = PredictiveDecisionContextBuilder().build(
        signal_only
    )

    result = PredictionExplainabilityEngine().explain(
        context
    )

    assert any(
        "limited number" in item
        for item in result.limitations
    )


def test_no_historical_evidence_is_explicitly_reported():
    signal = PredictiveSituation(
        prediction_id="PSIT-NOHISTORY",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        predicted_at=BASE,
        forecast_start=None,
        forecast_end=None,
        probability=0.40,
        confidence=0.40,
        severity="warning",
        prediction_sources=("predictive_signal",),
        evidence_situation_ids=(),
        evidence=("signal",),
    )

    context = PredictiveDecisionContextBuilder().build(
        signal
    )

    result = PredictionExplainabilityEngine().explain(
        context
    )

    assert any(
        "No historical situation IDs" in item
        for item in result.limitations
    )


def test_explanation_is_deterministic():
    engine = PredictionExplainabilityEngine()

    first = engine.explain(make_context())
    second = engine.explain(make_context())

    assert first == second


def test_explanation_id_is_deterministic():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert result.explanation_id == "EXPL-PSIT-PRED-S1"


def test_explain_many_preserves_order():
    engine = PredictionExplainabilityEngine()

    context1 = make_context()

    context2 = PredictiveDecisionContextBuilder().build(
        make_situation(
            probability=0.45,
            confidence=0.50,
            severity="warning",
        )
    )

    results = engine.explain_many(
        [context1, context2]
    )

    assert len(results) == 2
    assert results[0].prediction_id == "PSIT-PRED-S1"
    assert results[1].prediction_id == "PSIT-PRED-S1"


def test_uncertainty_is_inverse_of_confidence():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert result.uncertainty == 0.20
    assert result.uncertainty_level == "low"


def test_no_autonomous_action_is_created():
    result = PredictionExplainabilityEngine().explain(
        make_context()
    )

    assert result.requires_human_approval is True
