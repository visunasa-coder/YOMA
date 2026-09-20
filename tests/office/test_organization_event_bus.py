from __future__ import annotations

import pytest

from yoma.office.organization_events import OrganizationChangeEvent
from yoma.office.organization_event_bus import OrganizationEventBus


def make_event(
    event_type: str = "USER_ADDED",
    entity_id: str = "u1",
) -> OrganizationChangeEvent:
    return OrganizationChangeEvent(
        event_type=event_type,
        entity_type="user",
        entity_id=entity_id,
    )


def test_event_bus_starts_empty():
    bus = OrganizationEventBus()

    assert bus.subscriber_count() == 0


def test_subscribe_requires_callable():
    bus = OrganizationEventBus()

    with pytest.raises(TypeError):
        bus.subscribe("invalid")


def test_subscribe_adds_handler():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    bus.subscribe(handler)

    assert bus.subscriber_count() == 1


def test_duplicate_subscription_is_ignored():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    bus.subscribe(handler)
    bus.subscribe(handler)

    assert bus.subscriber_count() == 1


def test_unsubscribe_removes_handler():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    bus.subscribe(handler)

    assert bus.unsubscribe(handler) is True
    assert bus.subscriber_count() == 0


def test_unsubscribe_missing_handler_returns_false():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    assert bus.unsubscribe(handler) is False


def test_publish_requires_event():
    bus = OrganizationEventBus()

    with pytest.raises(TypeError):
        bus.publish("invalid")


def test_publish_delivers_event_to_subscriber():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)

    event = make_event()

    bus.publish(event)

    assert received == [event]


def test_publish_delivers_to_all_subscribers():
    bus = OrganizationEventBus()
    first = []
    second = []

    def first_handler(event):
        first.append(event)

    def second_handler(event):
        second.append(event)

    bus.subscribe(first_handler)
    bus.subscribe(second_handler)

    event = make_event()

    bus.publish(event)

    assert first == [event]
    assert second == [event]


def test_unsubscribed_handler_no_longer_receives_events():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)
    bus.unsubscribe(handler)

    bus.publish(make_event())

    assert received == []


def test_publish_many_requires_events():
    bus = OrganizationEventBus()

    with pytest.raises(TypeError):
        bus.publish_many(["invalid"])


def test_publish_many_delivers_events_in_order():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)

    first = make_event(
        event_type="USER_ADDED",
        entity_id="u1",
    )

    second = make_event(
        event_type="USER_UPDATED",
        entity_id="u1",
    )

    third = make_event(
        event_type="USER_REMOVED",
        entity_id="u1",
    )

    bus.publish_many([first, second, third])

    assert received == [first, second, third]


def test_publish_returns_number_of_successful_deliveries():
    bus = OrganizationEventBus()

    def first_handler(event):
        pass

    def second_handler(event):
        pass

    bus.subscribe(first_handler)
    bus.subscribe(second_handler)

    assert bus.publish(make_event()) == 2


def test_publish_many_returns_total_deliveries():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    bus.subscribe(handler)

    events = [
        make_event(entity_id="u1"),
        make_event(entity_id="u2"),
        make_event(entity_id="u3"),
    ]

    assert bus.publish_many(events) == 3


def test_subscriber_failure_does_not_stop_other_subscribers():
    bus = OrganizationEventBus()
    received = []

    def failing_handler(event):
        raise RuntimeError("subscriber failure")

    def working_handler(event):
        received.append(event)

    bus.subscribe(failing_handler)
    bus.subscribe(working_handler)

    with pytest.raises(RuntimeError):
        bus.publish(make_event())

    assert len(received) == 1