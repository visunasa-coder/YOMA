"""M29.9 full predictive intelligence end-to-end validation."""

from datetime import datetime, timedelta

from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.operations.situation import OperationalSituation
from yoma.office.predictive_intelligence_runtime import (
    PredictiveIntelligenceRuntime,
)


BASE = datetime(2026, 9, 1, 10, 0, 0)


def make_historical_pattern():
    return HistoricalPattern(
        pattern_id="HPAT-workload_pressure-ORG1-U1-GLOBAL-S1-S2",
        pattern_type="recurring_situation",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        occurrence_count=2,
        first_occurred_at=BASE - timedelta(days=14),
        last_occurred_at=BASE - timedelta(days=7),
        recurrence_intervals_seconds=(604800.0,),
        signal_combinations=(),
        situation_ids=("S1", "S2"),
    )


def make_baseline_trend():
    return BaselineTrend(
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        total_occurrences=4,
        historical_days=30,
        baseline_daily_frequency=0.13,
        recent_occurrences=2,
        previous_occurrences=1,
        window_days=7,
        recent_daily_frequency=0.29,
        previous_daily_frequency=0.14,
        frequency_change=0.15,
        deviation_from_baseline=1.23,
        trend_ratio=2.07,
        trend_direction="increasing",
        first_occurred_at=BASE - timedelta(days=30),
        last_occurred_at=BASE - timedelta(days=7),
        average_recurrence_interval_seconds=604800.0,
        situation_ids=("S1", "S2", "S3", "S4"),
    )


def make_situation(
    situation_id="CURRENT-1",
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=BASE,
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        severity="high",
        score=0.90,
        signal_ids=("SIG1",),
        evidence_event_ids=("EV1",),
    )


def make_runtime():
    return PredictiveIntelligenceRuntime(
        historical_patterns=(
            make_historical_pattern(),
        ),
        baseline_trends=(
            make_baseline_trend(),
        ),
    )


def test_full_pipeline_produces_every_layer():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert len(result.predictive_signals) == 1
    assert len(result.risk_forecasts) == 1
    assert len(result.recurrence_predictions) == 1
    assert len(result.workload_forecasts) == 1
    assert len(result.predictive_situations) == 1
    assert len(result.decision_contexts) == 1
    assert len(result.explanations) == 1


def test_prediction_identity_is_preserved_across_pipeline():
    result = make_runtime().analyze(
        [make_situation()]
    )

    signal_id = (
        result.predictive_signals[0].prediction_id
    )

    situation_id = (
        result.predictive_situations[0].prediction_id
    )

    context_id = (
        result.decision_contexts[0].prediction_id
    )

    explanation_id = (
        result.explanations[0].prediction_id
    )

    assert situation_id == f"PSIT-{signal_id}"
    assert context_id == situation_id
    assert explanation_id == situation_id


def test_risk_forecast_is_derived_from_predictive_signal():
    result = make_runtime().analyze(
        [make_situation()]
    )

    signal = result.predictive_signals[0]
    risk = result.risk_forecasts[0]

    assert risk.forecast_id == f"RISK-{signal.prediction_id}"
    assert 0.0 <= risk.risk_probability <= 1.0
    assert 0.0 <= risk.confidence <= 1.0


def test_recurrence_prediction_contains_historical_context():
    result = make_runtime().analyze(
        [make_situation()]
    )

    recurrence = result.recurrence_predictions[0]

    assert recurrence.historical_occurrences >= 2
    assert recurrence.historical_pattern_id is not None
    assert recurrence.historical_evidence_available is True
    assert recurrence.prediction_available is True


def test_workload_forecast_contains_baseline_context():
    result = make_runtime().analyze(
        [make_situation()]
    )

    workload = result.workload_forecasts[0]

    assert workload.historical_occurrences >= 2
    assert workload.historical_pattern_id is not None
    assert workload.forecast_available is True
    assert workload.above_baseline is True


def test_predictive_situation_combines_predictive_sources():
    result = make_runtime().analyze(
        [make_situation()]
    )

    prediction = result.predictive_situations[0]

    assert "predictive_signal" in (
        prediction.prediction_sources
    )
    assert "risk_forecast" in (
        prediction.prediction_sources
    )
    assert "recurrence_prediction" in (
        prediction.prediction_sources
    )
    assert "workload_forecast" in (
        prediction.prediction_sources
    )

    assert prediction.probability > 0.0
    assert prediction.confidence > 0.0
    assert prediction.detection_available is True


def test_predictive_decision_context_is_advisory():
    result = make_runtime().analyze(
        [make_situation()]
    )

    context = result.decision_contexts[0]

    assert context.decision_ready is True
    assert context.actions == ()
    assert context.requires_human_approval is True


def test_explainability_contains_evidence():
    result = make_runtime().analyze(
        [make_situation()]
    )

    explanation = result.explanations[0]

    assert explanation.explainable is True
    assert explanation.evidence_strength > 0.0
    assert explanation.confidence >= 0.0
    assert explanation.uncertainty >= 0.0
    assert explanation.factors
    assert explanation.explanation
    assert explanation.limitations


def test_historical_evidence_reaches_final_explanation():
    result = make_runtime().analyze(
        [make_situation()]
    )

    context = result.decision_contexts[0]
    explanation = result.explanations[0]

    assert context.historical_evidence_available is True
    assert explanation.evidence_situation_ids


def test_entire_pipeline_requires_human_review():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert result.requires_human_review is True

    assert all(
        context.requires_human_approval
        for context in result.decision_contexts
    )

    assert all(
        explanation.requires_human_approval
        for explanation in result.explanations
    )


def test_pipeline_is_deterministic_except_runtime_timestamps():
    runtime1 = make_runtime()
    runtime2 = make_runtime()

    result1 = runtime1.analyze(
        [make_situation()]
    )
    result2 = runtime2.analyze(
        [make_situation()]
    )

    assert result1.predictive_signals == (
        result2.predictive_signals
    )
    assert result1.risk_forecasts == (
        result2.risk_forecasts
    )
    assert result1.recurrence_predictions == (
        result2.recurrence_predictions
    )
    assert result1.workload_forecasts == (
        result2.workload_forecasts
    )

    assert (
        result1.predictive_situations[0].prediction_id
        == result2.predictive_situations[0].prediction_id
    )

    assert (
        result1.decision_contexts[0].context_id
        == result2.decision_contexts[0].context_id
    )

    assert (
        result1.explanations[0].explanation_id
        == result2.explanations[0].explanation_id
    )


def test_multiple_current_situations_flow_end_to_end():
    result = make_runtime().analyze(
        [
            make_situation("CURRENT-1"),
            make_situation("CURRENT-2"),
            make_situation("CURRENT-3"),
        ]
    )

    assert len(result.predictive_signals) == 3
    assert len(result.risk_forecasts) == 3
    assert len(result.recurrence_predictions) == 3
    assert len(result.workload_forecasts) == 3
    assert len(result.predictive_situations) == 3
    assert len(result.decision_contexts) == 3
    assert len(result.explanations) == 3

    assert len(
        {
            item.prediction_id
            for item in result.predictive_signals
        }
    ) == 3


def test_empty_pipeline_is_safe():
    result = make_runtime().analyze([])

    assert result.prediction_count == 0
    assert result.predictive_signals == ()
    assert result.risk_forecasts == ()
    assert result.recurrence_predictions == ()
    assert result.workload_forecasts == ()
    assert result.predictive_situations == ()
    assert result.decision_contexts == ()
    assert result.explanations == ()
    assert result.requires_human_review is False


def test_last_result_contains_complete_pipeline():
    runtime = make_runtime()

    result = runtime.analyze(
        [make_situation()]
    )

    assert runtime.last_result is result
    assert runtime.last_result.explanations


def test_no_executable_actions_exist_anywhere_in_m29():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert all(
        context.actions == ()
        for context in result.decision_contexts
    )

    assert all(
        context.requires_human_approval
        for context in result.decision_contexts
    )

    assert all(
        explanation.requires_human_approval
        for explanation in result.explanations
    )


def test_final_explanation_describes_prediction_reason():
    result = make_runtime().analyze(
        [make_situation()]
    )

    explanation = result.explanations[0]

    text = explanation.explanation.lower()

    assert "predicts" in text
    assert "probability" in text
    assert "confidence" in text
    assert "evidence" in text
    assert "human review" in text
