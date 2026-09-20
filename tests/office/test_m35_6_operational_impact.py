from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.cross_system_analytics import AnalyticsRecord
from yoma.office.intelligence.operational_impact import (
    OperationalImpactRuntime,
)


BASE = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def record(record_id, system):
    return AnalyticsRecord(
        record_id=record_id,
        source_system=system,
        record_type="event",
        observed_at=BASE,
    )


def test_calculates_total_manual_effort():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "calendar"),
            record("3", "slack"),
        ),
        manual_minutes_per_record=5,
    )

    assert result.total_records == 3
    assert result.estimated_manual_minutes == 15.0


def test_calculates_time_saved():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "calendar"),
            record("3", "slack"),
            record("4", "gmail"),
        ),
        manual_minutes_per_record=10,
        automation_savings_rate=0.50,
    )

    assert result.estimated_time_saved_minutes == 20.0
    assert result.estimated_time_saved_hours == 20.0 / 60.0


def test_calculates_savings_rate():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (record("1", "gmail"),),
        manual_minutes_per_record=10,
        automation_savings_rate=0.25,
    )

    assert result.estimated_savings_rate == 0.25
    assert result.estimated_time_saved_minutes == 2.5


def test_calculates_per_system_impact():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "gmail"),
            record("3", "calendar"),
        ),
        manual_minutes_per_record=10,
        automation_savings_rate=0.50,
    )

    assert len(result.system_impacts) == 2

    calendar = result.system_impacts[0]
    gmail = result.system_impacts[1]

    assert calendar.source_system == "calendar"
    assert calendar.record_count == 1
    assert calendar.estimated_manual_minutes == 10.0
    assert calendar.estimated_time_saved_minutes == 5.0

    assert gmail.source_system == "gmail"
    assert gmail.record_count == 2
    assert gmail.estimated_manual_minutes == 20.0
    assert gmail.estimated_time_saved_minutes == 10.0


def test_zero_savings_rate():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "gmail"),
        ),
        manual_minutes_per_record=10,
        automation_savings_rate=0,
    )

    assert result.estimated_manual_minutes == 20.0
    assert result.estimated_time_saved_minutes == 0.0


def test_full_savings_rate():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (
            record("1", "gmail"),
            record("2", "calendar"),
        ),
        manual_minutes_per_record=10,
        automation_savings_rate=1,
    )

    assert result.estimated_time_saved_minutes == 20.0


def test_empty_input():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(())

    assert result.total_records == 0
    assert result.estimated_manual_minutes == 0.0
    assert result.estimated_time_saved_minutes == 0.0
    assert result.system_impacts == ()


def test_rejects_negative_manual_time():
    runtime = OperationalImpactRuntime()

    with pytest.raises(ValueError):
        runtime.analyze((), manual_minutes_per_record=-1)


def test_rejects_invalid_savings_rate():
    runtime = OperationalImpactRuntime()

    with pytest.raises(ValueError):
        runtime.analyze((), automation_savings_rate=1.1)


def test_rejects_invalid_record():
    runtime = OperationalImpactRuntime()

    with pytest.raises(TypeError):
        runtime.analyze((object(),))


def test_rejects_naive_timestamp():
    runtime = OperationalImpactRuntime()

    invalid = AnalyticsRecord(
        record_id="1",
        source_system="gmail",
        record_type="event",
        observed_at=datetime(2026, 9, 6, 12, 0),
    )

    with pytest.raises(ValueError):
        runtime.analyze((invalid,))


def test_marks_result_as_estimate_only():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (record("1", "gmail"),)
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.metadata["analytics_only"] is True
    assert result.metadata["estimate_only"] is True
    assert result.metadata["observed_savings_not_claimed"] is True


def test_metadata_can_be_extended():
    runtime = OperationalImpactRuntime()

    result = runtime.analyze(
        (record("1", "gmail"),),
        metadata={"organization_id": "ORG1"},
    )

    assert result.metadata["organization_id"] == "ORG1"
