from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.intelligence.background_intelligence import (
    BackgroundEvent,
    BackgroundIntelligenceResult,
    BackgroundIntelligenceRuntime,
    BackgroundIntelligenceState,
)


BASE_TIME = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def event(
    event_id="evt-1",
    event_type="ticket.updated",
    source_system="jira",
    entity_id="ticket-1",
    offset=0,
):
    return BackgroundEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=BASE_TIME + timedelta(seconds=offset),
        source_system=source_system,
        entity_id=entity_id,
    )


def test_initial_state_is_stopped():
    runtime = BackgroundIntelligenceRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop_lifecycle():
    runtime = BackgroundIntelligenceRuntime()

    runtime.start()

    assert runtime.running is True

    runtime.stop()

    assert runtime.running is False


def test_start_is_idempotent():
    runtime = BackgroundIntelligenceRuntime()

    runtime.start()
    runtime.start()

    assert runtime.running is True


def test_stop_is_idempotent():
    runtime = BackgroundIntelligenceRuntime()

    runtime.stop()

    assert runtime.running is False


def test_processing_requires_running_runtime():
    runtime = BackgroundIntelligenceRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.process([event()])


def test_detects_background_event():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    result = runtime.process(
        [event()],
        detected_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundIntelligenceResult)
    assert result.processed_events == 1
    assert result.detected_events == 1
    assert len(result.work_items) == 1
    assert result.work_items[0].event_id == "evt-1"
    assert result.work_items[0].reason == "background_event_detected"


def test_processing_is_deterministic():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    result = runtime.process(
        [
            event("evt-2", offset=20),
            event("evt-1", offset=10),
        ],
        detected_at=BASE_TIME,
    )

    assert [item.event_id for item in result.work_items] == [
        "evt-1",
        "evt-2",
    ]


def test_duplicate_events_are_not_processed_twice():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    first = runtime.process([event()], detected_at=BASE_TIME)
    second = runtime.process([event()], detected_at=BASE_TIME)

    assert first.detected_events == 1
    assert second.detected_events == 0
    assert second.work_items == ()


def test_event_type_filter():
    runtime = BackgroundIntelligenceRuntime(
        event_types={"ticket.updated"}
    )
    runtime.start()

    result = runtime.process(
        [
            event("evt-1", "ticket.updated"),
            event("evt-2", "ticket.closed"),
        ],
        detected_at=BASE_TIME,
    )

    assert result.detected_events == 1
    assert result.work_items[0].event_type == "ticket.updated"


def test_invalid_event_is_rejected():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.process(["invalid"], detected_at=BASE_TIME)


def test_timezone_validation():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    naive = datetime(2026, 9, 6, 12, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.process([event()], detected_at=naive)


def test_work_items_never_become_executable():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    result = runtime.process([event()], detected_at=BASE_TIME)

    assert result.read_only is True
    assert result.executable is False

    item = result.work_items[0]

    assert item.requires_human_approval is True
    assert item.executable is False
    assert item.metadata["detection_only"] is True


def test_reset_allows_event_to_be_processed_again():
    runtime = BackgroundIntelligenceRuntime()
    runtime.start()

    first = runtime.process([event()], detected_at=BASE_TIME)

    runtime.reset()

    second = runtime.process([event()], detected_at=BASE_TIME)

    assert first.detected_events == 1
    assert second.detected_events == 1
