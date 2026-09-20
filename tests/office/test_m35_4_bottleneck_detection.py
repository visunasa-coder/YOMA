from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.bottleneck_detection import (
    BottleneckDetectionRuntime,
)
from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord


BASE = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def record(record_id, system):
    return AnalyticsRecord(
        record_id=record_id,
        source_system=system,
        record_type="event",
        observed_at=BASE,
    )


def test_detects_concentrated_system():
    runtime = BottleneckDetectionRuntime()

    records = (
        record("1", "gmail"),
        record("2", "gmail"),
        record("3", "gmail"),
        record("4", "gmail"),
        record("5", "calendar"),
        record("6", "slack"),
    )

    result = runtime.analyze(records, threshold_multiplier=1.5)

    assert len(result.candidates) == 1
    assert result.candidates[0].source_system == "gmail"
    assert result.candidates[0].record_count == 4


def test_calculates_share_of_total():
    runtime = BottleneckDetectionRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "gmail"),
            record("3", "calendar"),
            record("4", "slack"),
        )
    )

    assert result.candidates[0].share_of_total == 0.5


def test_calculates_excess_over_average():
    runtime = BottleneckDetectionRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "gmail"),
            record("3", "gmail"),
            record("4", "calendar"),
        ),
        threshold_multiplier=1.5,
    )

    candidate = result.candidates[0]

    assert result.average_records_per_system == 2.0
    assert candidate.excess_over_average == 1.0


def test_multiple_candidates_are_deterministically_sorted():
    runtime = BottleneckDetectionRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "gmail"),
            record("3", "gmail"),
            record("4", "calendar"),
            record("5", "calendar"),
            record("6", "calendar"),
            record("7", "slack"),
        ),
        threshold_multiplier=1.2,
    )

    assert tuple(c.source_system for c in result.candidates) == (
        "calendar",
        "gmail",
    )


def test_no_bottleneck_when_load_is_balanced():
    runtime = BottleneckDetectionRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "calendar"),
            record("3", "slack"),
        )
    )

    assert result.candidates == ()


def test_empty_input():
    runtime = BottleneckDetectionRuntime()

    result = runtime.analyze(())

    assert result.total_records == 0
    assert result.system_count == 0
    assert result.average_records_per_system == 0.0
    assert result.candidates == ()


def test_rejects_invalid_threshold():
    runtime = BottleneckDetectionRuntime()

    with pytest.raises(ValueError):
        runtime.analyze((), threshold_multiplier=0)


def test_rejects_invalid_record():
    runtime = BottleneckDetectionRuntime()

    with pytest.raises(TypeError):
        runtime.analyze((object(),))


def test_rejects_naive_timestamp():
    runtime = BottleneckDetectionRuntime()

    invalid = AnalyticsRecord(
        record_id="1",
        source_system="gmail",
        record_type="event",
        observed_at=datetime(2026, 9, 6, 12, 0),
    )

    with pytest.raises(ValueError):
        runtime.analyze((invalid,))


def test_enforces_read_only_boundary():
    runtime = BottleneckDetectionRuntime()

    result = runtime.analyze((record("1", "gmail"),))

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["analytics_only"] is True
    assert result.metadata["composition_only"] is True
