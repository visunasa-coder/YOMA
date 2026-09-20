from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.cross_system_analytics import (
    AnalyticsRecord,
    CrossSystemAnalyticsRuntime,
)


BASE = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def record(
    record_id,
    system,
    record_type,
    *,
    minutes=0,
):
    from datetime import timedelta

    return AnalyticsRecord(
        record_id=record_id,
        source_system=system,
        record_type=record_type,
        observed_at=BASE + timedelta(minutes=minutes),
    )


def test_aggregates_records_across_systems():
    runtime = CrossSystemAnalyticsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email"),
            record("2", "calendar", "meeting"),
            record("3", "gmail", "email"),
        )
    )

    assert result.total_records == 3
    assert result.systems == ("calendar", "gmail")
    assert result.records_by_system == {
        "calendar": 1,
        "gmail": 2,
    }


def test_aggregates_record_types():
    runtime = CrossSystemAnalyticsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email"),
            record("2", "calendar", "meeting"),
            record("3", "slack", "message"),
            record("4", "gmail", "email"),
        )
    )

    assert result.records_by_type == {
        "email": 2,
        "meeting": 1,
        "message": 1,
    }


def test_aggregates_system_and_type():
    runtime = CrossSystemAnalyticsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email"),
            record("2", "gmail", "email"),
            record("3", "calendar", "meeting"),
        )
    )

    assert result.records_by_system_and_type == {
        "calendar:meeting": 1,
        "gmail:email": 2,
    }


def test_filters_by_time_window():
    runtime = CrossSystemAnalyticsRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail", "email", minutes=-10),
            record("2", "calendar", "meeting"),
            record("3", "slack", "message", minutes=10),
        ),
        window_start=BASE,
        window_end=BASE,
    )

    assert result.total_records == 1
    assert result.systems == ("calendar",)


def test_empty_input_is_deterministic():
    runtime = CrossSystemAnalyticsRuntime()

    result = runtime.analyze(())

    assert result.total_records == 0
    assert result.systems == ()
    assert result.record_types == ()
    assert result.records_by_system == {}
    assert result.records_by_type == {}


def test_rejects_invalid_record_type():
    runtime = CrossSystemAnalyticsRuntime()

    with pytest.raises(TypeError):
        runtime.analyze((object(),))


def test_rejects_invalid_window():
    runtime = CrossSystemAnalyticsRuntime()

    with pytest.raises(ValueError):
        runtime.analyze(
            (),
            window_start=BASE,
            window_end=BASE.replace(hour=11),
        )


def test_enforces_read_only_boundary():
    runtime = CrossSystemAnalyticsRuntime()

    result = runtime.analyze(
        (record("1", "gmail", "email"),)
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["analytics_only"] is True
    assert result.metadata["composition_only"] is True


def test_analysis_does_not_mutate_input():
    runtime = CrossSystemAnalyticsRuntime()

    records = (
        record("1", "gmail", "email"),
        record("2", "calendar", "meeting"),
    )

    result = runtime.analyze(records)

    assert records == (
        record("1", "gmail", "email"),
        record("2", "calendar", "meeting"),
    )
    assert result.total_records == 2
