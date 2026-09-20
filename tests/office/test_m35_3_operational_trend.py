from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord
from yoma.office.intelligence.operational_trend import OperationalTrendRuntime


BASE = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def record(record_id, minutes=0):
    return AnalyticsRecord(
        record_id=record_id,
        source_system="gmail",
        record_type="email",
        observed_at=BASE + timedelta(minutes=minutes),
    )


def test_daily_trend_increases():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze(
        (
            record("1", 0),
            record("2", 24 * 60),
            record("3", 24 * 60),
            record("4", 24 * 60),
        )
    )

    trend = result.trends[0]

    assert trend.metric == "record_count"
    assert trend.direction == "increasing"
    assert trend.absolute_change == 2.0


def test_daily_trend_decreases():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze(
        (
            record("1", 0),
            record("2", 0),
            record("3", 24 * 60),
        )
    )

    trend = result.trends[0]

    assert trend.direction == "decreasing"
    assert trend.absolute_change == -1.0


def test_daily_trend_stable():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze(
        (
            record("1", 0),
            record("2", 24 * 60),
        )
    )

    trend = result.trends[0]

    assert trend.direction == "stable"
    assert trend.absolute_change == 0.0


def test_percentage_change():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze(
        (
            record("1", 0),
            record("2", 24 * 60),
            record("3", 24 * 60),
        )
    )

    trend = result.trends[0]

    assert trend.percentage_change == 100.0


def test_zero_baseline_has_no_percentage():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze(
        (
            record("1", 24 * 60),
            record("2", 24 * 60),
        )
    )

    trend = result.trends[0]

    assert trend.percentage_change is None


def test_single_period_is_stable():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze((record("1"),))

    trend = result.trends[0]

    assert result.period_count == 1
    assert trend.direction == "stable"
    assert trend.absolute_change == 0.0


def test_empty_input():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze(())

    assert result.trends == ()
    assert result.period_count == 0


def test_rejects_invalid_period():
    runtime = OperationalTrendRuntime()

    with pytest.raises(ValueError):
        runtime.analyze((record("1"),), period="month")


def test_rejects_invalid_record():
    runtime = OperationalTrendRuntime()

    with pytest.raises(TypeError):
        runtime.analyze((object(),))


def test_rejects_naive_timestamp():
    runtime = OperationalTrendRuntime()

    invalid = AnalyticsRecord(
        record_id="1",
        source_system="gmail",
        record_type="email",
        observed_at=datetime(2026, 9, 1, 12, 0),
    )

    with pytest.raises(ValueError):
        runtime.analyze((invalid,))


def test_enforces_read_only_boundary():
    runtime = OperationalTrendRuntime()

    result = runtime.analyze((record("1"),))

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["analytics_only"] is True
    assert result.metadata["composition_only"] is True
