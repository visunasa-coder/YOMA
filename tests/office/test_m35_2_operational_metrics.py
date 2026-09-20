from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord
from yoma.office.intelligence.operational_metrics import (
    OperationalMetricsRuntime,
)


BASE = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def record(record_id, system, record_type, minutes=0):
    return AnalyticsRecord(
        record_id=record_id,
        source_system=system,
        record_type=record_type,
        observed_at=BASE + timedelta(minutes=minutes),
    )


def test_calculates_basic_operational_metrics():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email", 0),
            record("2", "calendar", "meeting", 30),
            record("3", "gmail", "email", 60),
        )
    )

    assert result.total_records == 3
    assert result.active_systems == 2
    assert result.active_record_types == 2


def test_calculates_average_records_per_system():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email"),
            record("2", "gmail", "email"),
            record("3", "calendar", "meeting"),
        )
    )

    assert result.average_records_per_system == 1.5


def test_calculates_observation_span():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email", 0),
            record("2", "calendar", "meeting", 90),
        )
    )

    assert result.observation_span_seconds == 90 * 60


def test_calculates_records_per_hour():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email", 0),
            record("2", "calendar", "meeting", 30),
            record("3", "slack", "message", 60),
        )
    )

    assert result.records_per_hour == 3.0


def test_preserves_system_breakdown():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email"),
            record("2", "gmail", "email"),
            record("3", "calendar", "meeting"),
        )
    )

    assert result.records_by_system == {
        "calendar": 1,
        "gmail": 2,
    }


def test_empty_input_returns_zero_metrics():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(())

    assert result.total_records == 0
    assert result.active_systems == 0
    assert result.active_record_types == 0
    assert result.average_records_per_system == 0.0
    assert result.observation_span_seconds == 0.0
    assert result.records_per_hour == 0.0
    assert result.first_observed_at is None
    assert result.last_observed_at is None


def test_rejects_invalid_record():
    runtime = OperationalMetricsRuntime()

    with pytest.raises(TypeError):
        runtime.analyze((object(),))


def test_rejects_naive_timestamp():
    runtime = OperationalMetricsRuntime()

    invalid = AnalyticsRecord(
        record_id="1",
        source_system="gmail",
        record_type="email",
        observed_at=datetime(2026, 9, 6, 12, 0),
    )

    with pytest.raises(ValueError):
        runtime.analyze((invalid,))


def test_zero_length_window_has_zero_rate():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email"),
            record("2", "calendar", "meeting"),
        )
    )

    assert result.observation_span_seconds == 0.0
    assert result.records_per_hour == 0.0


def test_enforces_read_only_boundary():
    runtime = OperationalMetricsRuntime()

    result = runtime.analyze(
        (record("1", "gmail", "email"),)
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["analytics_only"] is True
