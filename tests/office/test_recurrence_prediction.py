from datetime import datetime, timedelta

import pytest

from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.operations.situation import OperationalSituation
from yoma.office.recurrence_prediction import (
    RecurrencePrediction,
    RecurrencePredictionEngine,
)


BASE = datetime(2026, 9, 1, 10, 0, 0)


def make_situation(
    sid="S1",
    when=BASE,
    organization_id="ORG1",
    user_id="U1",
):
    return OperationalSituation(
        situation_id=sid,
        situation_type="workload_pressure",
        detected_at=when,
        organization_id=organization_id,
        user_id=user_id,
        system_id=None,
        severity="warning",
        score=0.8,
        signal_ids=("SIG1",),
        evidence_event_ids=("EV1",),
        data={},
    )


def make_pattern():
    return HistoricalPattern(
        pattern_id=(
            "HPAT-workload_pressure-ORG1-U1-GLOBAL-S1-S2-S3"
        ),
        pattern_type="recurring_situation",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        occurrence_count=3,
        first_occurred_at=BASE - timedelta(days=14),
        last_occurred_at=BASE - timedelta(days=7),
        recurrence_intervals_seconds=(
            604800.0,
            604800.0,
        ),
        signal_combinations=(("workload.high",),),
        situation_ids=("S1", "S2", "S3"),
    )


def make_trend(
    direction="increasing",
    ratio=1.5,
    deviation=0.5,
):
    return BaselineTrend(
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        total_occurrences=3,
        historical_days=21,
        baseline_daily_frequency=0.142857,
        recent_occurrences=2,
        previous_occurrences=1,
        window_days=7,
        recent_daily_frequency=0.285714,
        previous_daily_frequency=0.142857,
        frequency_change=0.142857,
        deviation_from_baseline=deviation,
        trend_ratio=ratio,
        trend_direction=direction,
        first_occurred_at=BASE - timedelta(days=14),
        last_occurred_at=BASE - timedelta(days=1),
        average_recurrence_interval_seconds=604800.0,
        situation_ids=("S1", "S2", "S3"),
    )


def test_prediction_dataclass_defaults_to_human_approval():
    result = RecurrencePrediction(
        prediction_id="P1",
        prediction_type="recurrence_prediction",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        recurrence_probability=0.7,
        confidence=0.8,
        predicted_next_occurrence_start=BASE,
        predicted_next_occurrence_end=BASE + timedelta(hours=1),
        recurrence_interval_seconds=604800,
        historical_occurrences=3,
        trend_direction="increasing",
        trend_ratio=1.5,
        deviation_from_baseline=0.5,
        historical_pattern_id="HP1",
        evidence_situation_ids=("S1",),
        evidence=("history",),
    )

    assert result.requires_human_approval is True
    assert result.elevated is True
    assert result.prediction_available is True
    assert result.historical_evidence_available is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("recurrence_probability", -0.1),
        ("recurrence_probability", 1.1),
        ("confidence", -0.1),
        ("confidence", 1.1),
    ],
)
def test_probability_and_confidence_are_bounded(field, value):
    kwargs = dict(
        prediction_id="P1",
        prediction_type="recurrence_prediction",
        situation_type="x",
        organization_id=None,
        user_id=None,
        system_id=None,
        recurrence_probability=0.5,
        confidence=0.5,
        predicted_next_occurrence_start=None,
        predicted_next_occurrence_end=None,
        recurrence_interval_seconds=None,
        historical_occurrences=0,
        trend_direction="unknown",
        trend_ratio=1.0,
        deviation_from_baseline=0.0,
        historical_pattern_id=None,
        evidence_situation_ids=(),
        evidence=(),
    )

    kwargs[field] = value

    with pytest.raises(ValueError):
        RecurrencePrediction(**kwargs)


def test_engine_uses_explicit_matching_pattern_and_trend():
    result = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend()],
    ).predict(make_situation())

    assert result.historical_pattern_id == make_pattern().pattern_id
    assert result.historical_occurrences == 3
    assert result.recurrence_interval_seconds == 604800.0
    assert result.trend_direction == "increasing"
    assert result.predicted_next_occurrence_start is not None
    assert result.predicted_next_occurrence_end is not None
    assert (
        result.predicted_next_occurrence_start
        < result.predicted_next_occurrence_end
    )


def test_prediction_window_is_centered_on_expected_recurrence():
    result = RecurrencePredictionEngine(
        [make_pattern()]
    ).predict(make_situation())

    center = BASE + timedelta(seconds=604800)

    assert result.predicted_next_occurrence_start == (
        center - timedelta(seconds=151200)
    )

    assert result.predicted_next_occurrence_end == (
        center + timedelta(seconds=151200)
    )


def test_probability_is_bounded_and_deterministic():
    engine = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend()],
    )

    first = engine.predict(make_situation())
    second = engine.predict(make_situation())

    assert first == second
    assert 0.0 <= first.recurrence_probability <= 1.0
    assert 0.0 <= first.confidence <= 1.0


def test_increasing_trend_is_more_elevated_than_decreasing_trend():
    increasing = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend("increasing", 1.5, 0.5)],
    ).predict(make_situation())

    decreasing = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend("decreasing", 0.5, 0.5)],
    ).predict(make_situation())

    assert (
        increasing.recurrence_probability
        > decreasing.recurrence_probability
    )


def test_without_pattern_prediction_remains_conservative():
    result = RecurrencePredictionEngine(
        [],
        [make_trend()],
    ).predict(make_situation())

    assert result.historical_pattern_id is None
    assert result.recurrence_interval_seconds is None
    assert result.predicted_next_occurrence_start is None
    assert result.predicted_next_occurrence_end is None
    assert result.recurrence_probability < 0.60
    assert result.historical_evidence_available is False


def test_scope_isolation_prevents_cross_entity_matching():
    other = make_situation(
        "OTHER",
        organization_id="ORG2",
        user_id="U2",
    )

    result = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend()],
    ).predict(other)

    assert result.historical_pattern_id is None
    assert result.recurrence_interval_seconds is None


def test_predict_many_is_deterministic_and_ordered():
    engine = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend()],
    )

    results = engine.predict_many(
        [
            make_situation("S1"),
            make_situation("S2"),
        ]
    )

    assert len(results) == 2
    assert results[0].prediction_id != results[1].prediction_id


def test_invalid_window_fraction_is_rejected():
    with pytest.raises(ValueError):
        RecurrencePredictionEngine(window_fraction=0)

    with pytest.raises(ValueError):
        RecurrencePredictionEngine(window_fraction=0.51)


def test_evidence_explains_prediction():
    result = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend()],
    ).predict(make_situation())

    assert any(
        "historical_occurrences=3" in item
        for item in result.evidence
    )

    assert any(
        "trend_direction=increasing" in item
        for item in result.evidence
    )

    assert any(
        "recurrence_interval_seconds=604800.0" in item
        for item in result.evidence
    )


def test_no_autonomous_action_is_created():
    result = RecurrencePredictionEngine(
        [make_pattern()],
        [make_trend()],
    ).predict(make_situation())

    assert result.requires_human_approval is True
