from datetime import datetime, timedelta

import pytest

from yoma.office.predictive_situation import PredictiveSituation
from yoma.office.predictive_decision_context import (
    PredictiveDecisionContext,
    PredictiveDecisionContextBuilder,
    PredictiveDecisionRecommendation,
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


def test_recommendation_is_advisory():
    result = PredictiveDecisionRecommendation(
        recommendation_id="R1",
        recommendation_type="predictive_workload_pressure_review",
        reason="Review predicted workload pressure.",
        priority="high",
        target_user_id="U1",
        target_system_id=None,
        evidence=("evidence",),
    )

    assert result.requires_human_approval is True
    assert result.priority == "high"


def test_invalid_recommendation_priority_is_rejected():
    with pytest.raises(ValueError):
        PredictiveDecisionRecommendation(
            recommendation_id="R1",
            recommendation_type="test",
            reason="test",
            priority="invalid",
            target_user_id=None,
            target_system_id=None,
            evidence=(),
        )


def test_context_is_advisory_only():
    recommendation = PredictiveDecisionRecommendation(
        recommendation_id="R1",
        recommendation_type="predictive_review",
        reason="Review.",
        priority="high",
        target_user_id="U1",
        target_system_id=None,
        evidence=("evidence",),
    )

    context = PredictiveDecisionContext(
        context_id="C1",
        prediction_id="P1",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        created_at=BASE,
        probability=0.75,
        confidence=0.80,
        severity="high",
        forecast_start=NEXT,
        forecast_end=NEXT + timedelta(hours=1),
        recommendation=recommendation,
        evidence_situation_ids=("S1",),
        evidence=("evidence",),
    )

    assert context.requires_human_approval is True
    assert context.actions == ()
    assert context.decision_ready is True
    assert context.elevated is True


def test_executable_actions_are_rejected():
    recommendation = PredictiveDecisionRecommendation(
        recommendation_id="R1",
        recommendation_type="predictive_review",
        reason="Review.",
        priority="high",
        target_user_id="U1",
        target_system_id=None,
        evidence=(),
    )

    with pytest.raises(ValueError):
        PredictiveDecisionContext(
            context_id="C1",
            prediction_id="P1",
            situation_type="workload_pressure",
            organization_id="ORG1",
            user_id="U1",
            system_id=None,
            created_at=BASE,
            probability=0.75,
            confidence=0.80,
            severity="high",
            forecast_start=None,
            forecast_end=None,
            recommendation=recommendation,
            evidence_situation_ids=(),
            evidence=(),
            actions=("EXECUTE",),
        )


def test_builder_preserves_predictive_scope():
    result = PredictiveDecisionContextBuilder().build(
        make_situation()
    )

    assert result.organization_id == "ORG1"
    assert result.user_id == "U1"
    assert result.system_id is None
    assert result.prediction_id == "PSIT-PRED-S1"


def test_builder_creates_predictive_review_recommendation():
    result = PredictiveDecisionContextBuilder().build(
        make_situation()
    )

    assert (
        result.recommendation.recommendation_type
        == "predictive_workload_pressure_review"
    )

    assert result.recommendation.target_user_id == "U1"
    assert result.recommendation.priority == "high"
    assert result.recommendation.requires_human_approval is True


def test_builder_preserves_forecast_window():
    result = PredictiveDecisionContextBuilder().build(
        make_situation()
    )

    assert result.forecast_start == NEXT
    assert result.forecast_end == NEXT + timedelta(hours=2)


def test_builder_preserves_evidence():
    result = PredictiveDecisionContextBuilder().build(
        make_situation()
    )

    assert result.evidence_situation_ids == (
        "S1",
        "S2",
        "S3",
    )

    assert any(
        "prediction_id=PSIT-PRED-S1" in item
        for item in result.evidence
    )

    assert any(
        "prediction_sources=" in item
        for item in result.evidence
    )


def test_priority_follows_severity():
    builder = PredictiveDecisionContextBuilder()

    critical = builder.build(
        make_situation(
            probability=0.55,
            confidence=0.70,
            severity="critical",
        )
    )

    high = builder.build(
        make_situation(
            probability=0.55,
            confidence=0.70,
            severity="high",
        )
    )

    warning = builder.build(
        make_situation(
            probability=0.45,
            confidence=0.60,
            severity="warning",
        )
    )

    info = builder.build(
        make_situation(
            probability=0.20,
            confidence=0.30,
            severity="info",
        )
    )

    assert critical.recommendation.priority == "critical"
    assert high.recommendation.priority == "high"
    assert warning.recommendation.priority == "warning"
    assert info.recommendation.priority == "info"


def test_elevated_probability_promotes_priority():
    result = PredictiveDecisionContextBuilder().build(
        make_situation(
            probability=0.70,
            confidence=0.50,
            severity="info",
        )
    )

    assert result.recommendation.priority == "high"


def test_context_id_is_deterministic():
    builder = PredictiveDecisionContextBuilder()

    first = builder.build(make_situation())
    second = builder.build(make_situation())

    assert first == second
    assert first.context_id == "PDEC-PSIT-PRED-S1"


def test_build_many_preserves_order():
    builder = PredictiveDecisionContextBuilder()

    results = builder.build_many(
        [
            make_situation(),
            make_situation(
                probability=0.40,
                confidence=0.50,
                severity="warning",
            ),
        ]
    )

    assert len(results) == 2
    assert results[0].prediction_id == results[1].prediction_id
    assert results[0].recommendation.priority == "high"
    assert results[1].recommendation.priority == "warning"


def test_no_autonomous_action_path_exists():
    result = PredictiveDecisionContextBuilder().build(
        make_situation()
    )

    assert result.actions == ()
    assert result.requires_human_approval is True
    assert result.recommendation.requires_human_approval is True


def test_historical_evidence_is_preserved():
    result = PredictiveDecisionContextBuilder().build(
        make_situation()
    )

    assert result.historical_evidence_available is True
    assert result.evidence_situation_ids == (
        "S1",
        "S2",
        "S3",
    )
