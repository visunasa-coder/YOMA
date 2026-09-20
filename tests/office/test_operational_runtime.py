from datetime import datetime, timezone

import pytest

from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.intelligence.operational_runtime import (
    OperationalIntelligenceRuntime,
)
from yoma.office.operations import (
    OperationalEvent,
    OperationalEventBus,
)


def event(
    event_id: str,
    event_type: str,
    user_id: str | None = "U001",
    data: dict | None = None,
):
    return OperationalEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        user_id=user_id,
        source="test",
        data=data or {},
    )


def make_runtime(
    event_bus: OperationalEventBus | None = None,
) -> OperationalIntelligenceRuntime:
    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    return OperationalIntelligenceRuntime(
        intelligence_engine=engine,
        event_bus=event_bus,
    )


def test_runtime_processes_events_into_signals():
    runtime = make_runtime()

    result = runtime.process([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.9},
        )
    ])

    assert len(result.events) == 1
    assert len(result.signals) == 1
    assert result.signals[0].signal_type == "workload.high"
    assert result.signals[0].score == 0.9


def test_runtime_preserves_event_order():
    runtime = make_runtime()

    events = [
        event("EV001", "attendance.check_in"),
        event("EV002", "workload.high", data={"score": 0.8}),
    ]

    result = runtime.process(events)

    assert [item.event_id for item in result.events] == [
        "EV001",
        "EV002",
    ]


def test_runtime_process_event():
    runtime = make_runtime()

    source_event = event(
        "EV001",
        "workload.high",
        data={"score": 0.85},
    )

    result = runtime.process_event(source_event)

    assert result.events == (source_event,)
    assert len(result.signals) == 1


def test_runtime_rejects_invalid_event_input():
    runtime = make_runtime()

    with pytest.raises(TypeError):
        runtime.process(["not an event"])


def test_runtime_subscribes_to_event_bus():
    bus = OperationalEventBus()
    runtime = make_runtime(bus)

    assert bus.subscriber_count == 1

    runtime.close()

    assert bus.subscriber_count == 0


def test_runtime_receives_published_event():
    bus = OperationalEventBus()
    runtime = make_runtime(bus)

    runtime.start()

    bus.publish(
        event(
            "EV001",
            "workload.high",
            data={"score": 0.95},
        )
    )

    assert runtime.last_result is not None
    assert len(runtime.last_result.events) == 1
    assert len(runtime.last_result.signals) == 1


def test_runtime_start_and_stop():
    bus = OperationalEventBus()
    runtime = make_runtime(bus)

    assert runtime.running is False

    runtime.start()

    assert runtime.running is True

    runtime.stop()

    assert runtime.running is False


def test_runtime_does_not_process_bus_events_when_stopped():
    bus = OperationalEventBus()
    runtime = make_runtime(bus)

    runtime.stop()

    bus.publish(
        event(
            "EV001",
            "workload.high",
            data={"score": 0.95},
        )
    )

    assert runtime.last_result is None
