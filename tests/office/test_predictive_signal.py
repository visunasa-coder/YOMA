from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.operations.situation import OperationalSituation
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.baseline_trend import BaselineTrend
from yoma.office.predictive_signal import (
    PredictiveSignal,
    PredictiveSignalEngine,
)


def situation(
    situation_id="current",
    situation_type="workload_pressure",
    organization_id="org-1",
    user_id="user-1",
    system_id=None,
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type=situation_type,
        detected_at=datetime(
            2026, 1, 10, 10, 0,
            tzinfo=timezone.utc,
        ),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        severity="warning",
        score=0.9,
        signal_ids=("sig-1",),
        evidence_event_ids=("evt-1",),
        data={},
    )


def pattern(
    occurrence_count=5,
):
    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    return HistoricalPattern(
        pattern_id="HPAT-workload_pressure-org-1-user-1-GLOBAL-s1-s2",
        pattern_type="historical_recurrence",
        situation_type="workload_pressure",
        organization_id="org-1",
        user_id="user-1",
        system_id=None,
        occurrence_count=occurrence_count,
        first_occurred_at=base,
        last_occurred_at=base + timedelta(days=9),
        recurrence_intervals_seconds=(
            172800.0,
            172800.0,
        ),
        signal_combinations=(("sig-1",),),
        situation_ids=("s1", "s2", "s3"),
    )


def trend(
    direction="increasing",
):
    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    return BaselineTrend(
        situation_type="workload_pressure",
        organization_id="org-1",
        user_id="user-1",
        system_id=None,
        total_occurrences=5,
        historical_days=10.0,
        baseline_daily_frequency=0.5,
        recent_occurrences=4,
        previous_occurrences=1,
        window_days=7.0,
        recent_daily_frequency=4 / 7,
        previous_daily_frequency=1 / 7,
        frequency_change=3 / 7,
        deviation_from_baseline=0.142857,
        trend_ratio=4.0,
        trend_direction=direction,
        first_occurred_at=base,
        last_occurred_at=base + timedelta(days=9),
        average_recurrence_interval_seconds=172800.0,
        situation_ids=("s1", "s2", "s3"),
    )


def test_builds_predictive_signal():
    result = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    ).predict(situation())

    assert isinstance(result, PredictiveSignal)
    assert result.prediction_type == "recurrence_prediction"
    assert result.situation_type == "workload_pressure"
    assert result.historical_occurrences == 5
    assert result.historical_pattern_id is not None


def test_likelihood_is_bounded():
    result = PredictiveSignalEngine(
        [pattern(100)],
        [trend()],
    ).predict(situation())

    assert 0.0 <= result.recurrence_likelihood <= 1.0


def test_confidence_is_bounded():
    result = PredictiveSignalEngine(
        [pattern(100)],
        [trend()],
    ).predict(situation())

    assert 0.0 <= result.confidence <= 1.0


def test_increasing_trend_produces_elevated_prediction():
    result = PredictiveSignalEngine(
        [pattern()],
        [trend("increasing")],
    ).predict(situation())

    assert result.elevated is True
    assert result.trend_direction == "increasing"


def test_decreasing_trend_reduces_prediction():
    increasing = PredictiveSignalEngine(
        [pattern()],
        [trend("increasing")],
    ).predict(situation())

    decreasing = PredictiveSignalEngine(
        [pattern()],
        [trend("decreasing")],
    ).predict(situation())

    assert (
        decreasing.recurrence_likelihood
        < increasing.recurrence_likelihood
    )


def test_predicts_next_occurrence_window():
    result = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    ).predict(situation())

    assert result.predicted_next_occurrence_start is not None
    assert result.predicted_next_occurrence_end is not None
    assert (
        result.predicted_next_occurrence_start
        < result.predicted_next_occurrence_end
    )


def test_preserves_scope():
    result = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    ).predict(situation())

    assert result.organization_id == "org-1"
    assert result.user_id == "user-1"
    assert result.system_id is None


def test_preserves_historical_evidence():
    result = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    ).predict(situation())

    assert result.historical_evidence_available is True
    assert result.evidence_situation_ids == (
        "s1",
        "s2",
        "s3",
    )


def test_prediction_id_is_deterministic():
    engine = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    )

    first = engine.predict(situation())
    second = engine.predict(situation())

    assert first.prediction_id == second.prediction_id


def test_no_history_is_safe():
    result = PredictiveSignalEngine(
        [],
        [],
    ).predict(situation())

    assert result.recurrence_likelihood == 0.0
    assert result.confidence == 0.0
    assert result.predicted_next_occurrence_start is None
    assert result.predicted_next_occurrence_end is None
    assert result.historical_pattern_id is None
    assert result.historical_evidence_available is False


def test_scope_matching_is_explicit():
    wrong = pattern()

    wrong = HistoricalPattern(
        pattern_id="wrong",
        pattern_type=wrong.pattern_type,
        situation_type=wrong.situation_type,
        organization_id="org-2",
        user_id=wrong.user_id,
        system_id=wrong.system_id,
        occurrence_count=99,
        first_occurred_at=wrong.first_occurred_at,
        last_occurred_at=wrong.last_occurred_at,
        recurrence_intervals_seconds=wrong.recurrence_intervals_seconds,
        signal_combinations=wrong.signal_combinations,
        situation_ids=("wrong",),
    )

    result = PredictiveSignalEngine(
        [wrong],
        [],
    ).predict(situation())

    assert result.historical_pattern_id is None
    assert result.recurrence_likelihood == 0.0


def test_predict_many():
    engine = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    )

    results = engine.predict_many(
        [
            situation("s1"),
            situation("s2"),
        ]
    )

    assert len(results) == 2
    assert results[0].prediction_id != results[1].prediction_id


def test_human_approval_required():
    result = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    ).predict(situation())

    assert result.requires_human_approval is True


def test_invalid_pattern_rejected():
    with pytest.raises(TypeError):
        PredictiveSignalEngine(
            [object()],
            [],
        )


def test_invalid_trend_rejected():
    with pytest.raises(TypeError):
        PredictiveSignalEngine(
            [],
            [object()],
        )


def test_invalid_situation_rejected():
    engine = PredictiveSignalEngine(
        [pattern()],
        [trend()],
    )

    with pytest.raises(TypeError):
        engine.predict(object())
