from datetime import datetime, timedelta

from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.baseline_trend import BaselineTrend
from yoma.office.operations.situation import OperationalSituation
from yoma.office.predictive_intelligence_runtime import (
    PredictiveIntelligenceRuntime,
)


BASE = datetime(2026, 9, 1, 10, 0, 0)


def make_situation(
    situation_id="S1",
    detected_at=BASE,
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=detected_at,
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        severity="high",
        score=0.90,
        signal_ids=("SIG1",),
        evidence_event_ids=("EV1",),
    )


def make_pattern():
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


def make_trend():
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


def make_runtime():
    return PredictiveIntelligenceRuntime(
        historical_patterns=(make_pattern(),),
        baseline_trends=(make_trend(),),
    )


def test_runtime_returns_complete_pipeline():
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


def test_prediction_count():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert result.prediction_count == 1


def test_elevated_predictions_are_available():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert result.elevated_situations


def test_human_review_is_required():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert result.requires_human_review is True


def test_explanation_matches_decision_context():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert (
        result.explanations[0].prediction_id
        == result.decision_contexts[0].prediction_id
    )


def test_last_result_is_retained():
    runtime = make_runtime()

    result = runtime.analyze(
        [make_situation()]
    )

    assert runtime.last_result == result


def test_clear_last_result():
    runtime = make_runtime()

    runtime.analyze(
        [make_situation()]
    )

    runtime.clear_last_result()

    assert runtime.last_result is None


def test_empty_input_is_deterministic():
    result = make_runtime().analyze([])

    assert result.predictive_signals == ()
    assert result.risk_forecasts == ()
    assert result.recurrence_predictions == ()
    assert result.workload_forecasts == ()
    assert result.predictive_situations == ()
    assert result.decision_contexts == ()
    assert result.explanations == ()


def test_multiple_situations_are_preserved():
    result = make_runtime().analyze(
        [
            make_situation("S1"),
            make_situation("S2"),
        ]
    )

    assert len(result.predictive_signals) == 2
    assert len(result.risk_forecasts) == 2
    assert len(result.recurrence_predictions) == 2
    assert len(result.workload_forecasts) == 2
    assert len(result.predictive_situations) == 2
    assert len(result.decision_contexts) == 2
    assert len(result.explanations) == 2


def test_contexts_have_no_executable_actions():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert result.decision_contexts[0].actions == ()


def test_explanations_require_human_approval():
    result = make_runtime().analyze(
        [make_situation()]
    )

    assert (
        result.explanations[0].requires_human_approval
        is True
    )
