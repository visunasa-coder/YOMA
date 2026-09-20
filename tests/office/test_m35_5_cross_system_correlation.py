from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord
from yoma.office.intelligence.cross_system_correlation import (
    CrossSystemCorrelationRuntime,
)


BASE = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def record(record_id, system, seconds=0):
    return AnalyticsRecord(
        record_id=record_id,
        source_system=system,
        record_type="event",
        observed_at=BASE + timedelta(seconds=seconds),
    )


def test_correlates_activity_within_window():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "calendar", 60),
        ),
        window_seconds=300,
    )

    assert len(result.correlations) == 1
    correlation = result.correlations[0]

    assert correlation.source_system == "calendar"
    assert correlation.related_system == "gmail"
    assert correlation.related_pair_count == 1
    assert correlation.correlation_rate == 1.0


def test_ignores_activity_outside_window():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "calendar", 600),
        ),
        window_seconds=300,
    )

    assert result.correlations == ()


def test_zero_window_requires_same_timestamp():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "calendar", 0),
        ),
        window_seconds=0,
    )

    assert len(result.correlations) == 1


def test_multiple_system_pairs_are_reported():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "calendar", 30),
            record("3", "slack", 60),
        ),
        window_seconds=120,
    )

    assert len(result.correlations) == 3


def test_same_system_is_not_correlated_with_itself():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "gmail", 30),
        ),
        window_seconds=120,
    )

    assert result.correlations == ()


def test_correlation_rate_is_based_on_source_records():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "gmail", 1000),
            record("3", "calendar", 20),
        ),
        window_seconds=60,
    )

    correlation = result.correlations[0]

    assert correlation.source_system == "calendar"
    assert correlation.related_system == "gmail"
    assert correlation.source_record_count == 1
    assert correlation.related_record_count == 2
    assert correlation.related_pair_count == 1
    assert correlation.correlation_rate == 1.0

def test_results_are_deterministically_sorted():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", 0),
            record("2", "calendar", 10),
            record("3", "slack", 20),
        ),
        window_seconds=60,
    )

    pairs = tuple(
        (item.source_system, item.related_system)
        for item in result.correlations
    )

    assert pairs == (
        ("calendar", "gmail"),
        ("calendar", "slack"),
        ("gmail", "slack"),
    )


def test_empty_input():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze(())

    assert result.total_records == 0
    assert result.correlations == ()


def test_rejects_negative_window():
    runtime = CrossSystemCorrelationRuntime()

    with pytest.raises(ValueError):
        runtime.analyze((), window_seconds=-1)


def test_rejects_invalid_record():
    runtime = CrossSystemCorrelationRuntime()

    with pytest.raises(TypeError):
        runtime.analyze((object(),))


def test_rejects_naive_timestamp():
    runtime = CrossSystemCorrelationRuntime()

    invalid = AnalyticsRecord(
        record_id="1",
        source_system="gmail",
        record_type="event",
        observed_at=datetime(2026, 9, 6, 12, 0),
    )

    with pytest.raises(ValueError):
        runtime.analyze((invalid,))


def test_enforces_read_only_boundary():
    runtime = CrossSystemCorrelationRuntime()

    result = runtime.analyze((record("1", "gmail"),))

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["analytics_only"] is True
    assert result.metadata["composition_only"] is True
