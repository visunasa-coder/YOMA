from datetime import datetime, timezone

from yoma.office.operations import (
    OperationalAction,
    OperationalEvent,
    OperationalEventBus,
    OperationalSignal,
)


def make_event(**kwargs):
    values = {
        "event_id": "EV001",
        "event_type": "attendance.check_in",
        "occurred_at": datetime.now(timezone.utc),
        "organization_id": "ORG001",
        "user_id": "U001",
        "source": "attendance",
    }
    values.update(kwargs)
    return OperationalEvent(**values)


def test_operational_event():
    event = make_event()

    assert event.event_id == "EV001"
    assert event.event_type == "attendance.check_in"
    assert event.is_user_event is True
    assert event.is_system_event is False


def test_system_event():
    event = make_event(
        user_id=None,
        system_id="SYS001",
        event_type="hardware.device_online",
    )

    assert event.is_user_event is False
    assert event.is_system_event is True


def test_operational_action_defaults_to_approval():
    action = OperationalAction(
        action_id="ACT001",
        action_type="workload.review",
        target_user_id="U001",
    )

    assert action.requires_approval is True


def test_operational_signal():
    signal = OperationalSignal(
        signal_id="SIG001",
        signal_type="workload.high",
        detected_at=datetime.now(timezone.utc),
        user_id="U001",
        score=0.85,
        severity="warning",
        evidence_event_ids=("EV001", "EV002"),
    )

    assert signal.score == 0.85
    assert signal.evidence_event_ids == ("EV001", "EV002")


def test_event_bus_publish():
    bus = OperationalEventBus()
    received = []

    bus.subscribe(received.append)

    event = make_event()

    bus.publish(event)

    assert bus.subscriber_count == 1
    assert received == [event]


def test_event_bus_publish_many():
    bus = OperationalEventBus()
    received = []

    bus.subscribe(received.append)

    events = [
        make_event(event_id="EV001"),
        make_event(event_id="EV002"),
        make_event(event_id="EV003"),
    ]

    bus.publish_many(events)

    assert received == events


def test_event_bus_duplicate_subscription_is_ignored():
    bus = OperationalEventBus()
    received = []

    bus.subscribe(received.append)
    bus.subscribe(received.append)

    bus.publish(make_event())

    assert bus.subscriber_count == 1
    assert len(received) == 1


def test_event_bus_unsubscribe():
    bus = OperationalEventBus()
    received = []

    bus.subscribe(received.append)
    bus.unsubscribe(received.append)

    bus.publish(make_event())

    assert bus.subscriber_count == 0
    assert received == []
