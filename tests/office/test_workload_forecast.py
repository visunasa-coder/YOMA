from datetime import datetime, timedelta

import pytest

from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.operations.situation import OperationalSituation
from yoma.office.workload_forecast import (
    WorkloadForecast,
    WorkloadForecastEngine,
)


BASE = datetime(2026, 9, 1, 10, 0, 0)


def make_situation(
    sid="S1",
    organization_id="ORG1",
    user_id="U1",
):
    return OperationalSituation(
        situation_id=sid,
        situation_type="workload_pressure",
        detected_at=BASE,
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


def test_forecast_dataclass_is_advisory():
    result = WorkloadForecast(
        forecast_id="W1",
        forecast_type="workload_forecast",
        situation_type="workload_pressure",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        forecast_start=BASE,
        forecast_end=BASE + timedelta(days=7),
        baseline_daily_frequency=0.1,
        forecast_daily_frequency=0.2,
        recent_daily_frequency=0.15,
        previous_daily_frequency=0.1,
        frequency_change=0.05,
        deviation_from_baseline=0.5,
        trend_ratio=1.5,
        trend_direction="increasing",
        workload_probability=0.7,
        confidence=0.8,
        historical_occurrences=3,
        historical_pattern_id="HP1",
        evidence_situation_ids=("S1",),
        evidence=("trend",),
    )

    assert result.requires_human_approval is True
    assert result.elevated is True
    assert result.forecast_available is True
    assert result.above_baseline is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("workload_probability", -0.1),
        ("workload_probability", 1.1),
        ("confidence", -0.1),
        ("confidence", 1.1),
        ("baseline_daily_frequency", -0.1),
        ("forecast_daily_frequency", -0.1),
    ],
)
def test_forecast_values_are_validated(field, value):
    kwargs = dict(
        forecast_id="W1",
        forecast_type="workload_forecast",
        situation_type="x",
        organization_id=None,
        user_id=None,
        system_id=None,
        forecast_start=None,
        forecast_end=None,
        baseline_daily_frequency=0.0,
        forecast_daily_frequency=0.0,
        recent_daily_frequency=0.0,
        previous_daily_frequency=0.0,
        frequency_change=0.0,
        deviation_from_baseline=0.0,
        trend_ratio=1.0,
        trend_direction="unknown",
        workload_probability=0.5,
        confidence=0.5,
        historical_occurrences=0,
        historical_pattern_id=None,
        evidence_situation_ids=(),
        evidence=(),
    )

    kwargs[field] = value

    with pytest.raises(ValueError):
        WorkloadForecast(**kwargs)


def test_engine_uses_explicit_matching_trend():
    result = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    ).forecast(make_situation())

    assert result.historical_pattern_id == make_pattern().pattern_id
    assert result.historical_occurrences == 3
    assert result.trend_direction == "increasing"
    assert result.baseline_daily_frequency == 0.142857
    assert result.recent_daily_frequency == 0.285714
    assert result.previous_daily_frequency == 0.142857
    assert result.forecast_daily_frequency == 0.428571


def test_forecast_window_defaults_to_seven_days():
    result = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    ).forecast(make_situation())

    assert result.forecast_start == BASE
    assert result.forecast_end == BASE + timedelta(days=7)


def test_forecast_frequency_is_never_negative():
    base = make_trend(
        direction="decreasing",
        ratio=0.2,
        deviation=-0.8,
    )

    decreasing = BaselineTrend(
        situation_type=base.situation_type,
        organization_id=base.organization_id,
        user_id=base.user_id,
        system_id=base.system_id,
        total_occurrences=base.total_occurrences,
        historical_days=base.historical_days,
        baseline_daily_frequency=base.baseline_daily_frequency,
        recent_occurrences=base.recent_occurrences,
        previous_occurrences=base.previous_occurrences,
        window_days=base.window_days,
        recent_daily_frequency=0.05,
        previous_daily_frequency=0.50,
        frequency_change=-0.45,
        deviation_from_baseline=-0.65,
        trend_ratio=0.1,
        trend_direction="decreasing",
        first_occurred_at=base.first_occurred_at,
        last_occurred_at=base.last_occurred_at,
        average_recurrence_interval_seconds=(
            base.average_recurrence_interval_seconds
        ),
        situation_ids=base.situation_ids,
    )

    result = WorkloadForecastEngine(
        [make_pattern()],
        [decreasing],
    ).forecast(make_situation())

    assert result.forecast_daily_frequency == 0.0


def test_increasing_trend_has_higher_workload_probability():
    increasing = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend("increasing", 1.5, 0.5)],
    ).forecast(make_situation())

    decreasing = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend("decreasing", 0.5, -0.2)],
    ).forecast(make_situation())

    assert (
        increasing.workload_probability
        > decreasing.workload_probability
    )


def test_without_trend_remains_conservative():
    result = WorkloadForecastEngine(
        [make_pattern()],
        [],
    ).forecast(make_situation())

    assert result.trend_direction == "unknown"
    assert result.forecast_daily_frequency == 0.0
    assert result.workload_probability < 0.60
    assert result.workload_probability == 0.29
    assert result.confidence == 0.385


def test_scope_isolation_prevents_cross_entity_matching():
    other = make_situation(
        "OTHER",
        organization_id="ORG2",
        user_id="U2",
    )

    result = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    ).forecast(other)

    assert result.historical_pattern_id is None
    assert result.trend_direction == "unknown"
    assert result.forecast_daily_frequency == 0.0


def test_prediction_ids_are_deterministic_and_per_situation():
    engine = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    )

    first = engine.forecast(make_situation("S1"))
    second = engine.forecast(make_situation("S2"))

    assert first == engine.forecast(make_situation("S1"))
    assert first.forecast_id != second.forecast_id


def test_forecast_many_preserves_order():
    engine = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    )

    results = engine.forecast_many(
        [
            make_situation("S1"),
            make_situation("S2"),
        ]
    )

    assert len(results) == 2
    assert results[0].forecast_id != results[1].forecast_id


def test_invalid_forecast_days_are_rejected():
    with pytest.raises(ValueError):
        WorkloadForecastEngine(forecast_days=0)

    with pytest.raises(ValueError):
        WorkloadForecastEngine(forecast_days=-1)


def test_evidence_explains_workload_forecast():
    result = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    ).forecast(make_situation())

    assert any(
        "baseline_daily_frequency=0.142857" in item
        for item in result.evidence
    )

    assert any(
        "forecast_daily_frequency=0.428571" in item
        for item in result.evidence
    )

    assert any(
        "trend_direction=increasing" in item
        for item in result.evidence
    )


def test_no_autonomous_action_is_created():
    result = WorkloadForecastEngine(
        [make_pattern()],
        [make_trend()],
    ).forecast(make_situation())

    assert result.requires_human_approval is True
