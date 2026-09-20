from __future__ import annotations

import pytest

from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_events import OrganizationChangeEvent


def make_event(
    event_type: str = "USER_ADDED",
    entity_type: str = "user",
    entity_id: str = "u1",
) -> OrganizationChangeEvent:
    return OrganizationChangeEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def test_subscribe_can_filter_by_event_type():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        handler,
        event_types={"USER_ADDED"},
    )

    bus.publish(make_event("USER_ADDED"))
    bus.publish(make_event("USER_UPDATED"))

    assert len(received) == 1
    assert received[0].event_type == "USER_ADDED"


def test_subscribe_can_filter_by_entity_type():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        handler,
        entity_types={"system"},
    )

    bus.publish(
        make_event(
            "SYSTEM_ADDED",
            "system",
            "s1",
        )
    )

    bus.publish(
        make_event(
            "USER_ADDED",
            "user",
            "u1",
        )
    )

    assert len(received) == 1
    assert received[0].entity_type == "system"


def test_subscriber_without_filters_receives_all_events():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)

    bus.publish(make_event("USER_ADDED"))
    bus.publish(
        make_event(
            "SYSTEM_ADDED",
            "system",
            "s1",
        )
    )

    assert len(received) == 2


def test_subscriber_can_use_both_event_and_entity_filters():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        handler,
        event_types={"USER_ADDED"},
        entity_types={"user"},
    )

    bus.publish(
        make_event(
            "USER_ADDED",
            "user",
            "u1",
        )
    )

    bus.publish(
        make_event(
            "USER_ADDED",
            "system",
            "s1",
        )
    )

    bus.publish(
        make_event(
            "USER_UPDATED",
            "user",
            "u2",
        )
    )

    assert len(received) == 1
    assert received[0].entity_id == "u1"


def test_event_type_filter_accepts_multiple_types():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        handler,
        event_types={
            "USER_ADDED",
            "USER_REMOVED",
        },
    )

    bus.publish(make_event("USER_ADDED"))
    bus.publish(make_event("USER_UPDATED"))
    bus.publish(make_event("USER_REMOVED"))

    assert [
        event.event_type
        for event in received
    ] == [
        "USER_ADDED",
        "USER_REMOVED",
    ]


def test_entity_type_filter_accepts_multiple_types():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        handler,
        entity_types={
            "user",
            "system",
        },
    )

    bus.publish(
        make_event(
            "USER_ADDED",
            "user",
            "u1",
        )
    )

    bus.publish(
        make_event(
            "SYSTEM_ADDED",
            "system",
            "s1",
        )
    )

    bus.publish(
        make_event(
            "OTHER",
            "other",
            "x1",
        )
    )

    assert len(received) == 2


def test_empty_event_type_filter_is_rejected():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    with pytest.raises(ValueError):
        bus.subscribe(
            handler,
            event_types=set(),
        )


def test_empty_entity_type_filter_is_rejected():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    with pytest.raises(ValueError):
        bus.subscribe(
            handler,
            entity_types=set(),
        )


def test_invalid_event_type_filter_is_rejected():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    with pytest.raises(TypeError):
        bus.subscribe(
            handler,
            event_types="USER_ADDED",
        )


def test_invalid_entity_type_filter_is_rejected():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    with pytest.raises(TypeError):
        bus.subscribe(
            handler,
            entity_types="user",
        )


def test_filtered_subscriber_does_not_affect_other_subscribers():
    bus = OrganizationEventBus()
    filtered = []
    all_events = []

    def filtered_handler(event):
        filtered.append(event)

    def all_handler(event):
        all_events.append(event)

    bus.subscribe(
        filtered_handler,
        event_types={"USER_ADDED"},
    )

    bus.subscribe(all_handler)

    user_event = make_event("USER_ADDED")

    system_event = make_event(
        "SYSTEM_ADDED",
        "system",
        "s1",
    )

    bus.publish(user_event)
    bus.publish(system_event)

    assert filtered == [user_event]
    assert all_events == [
        user_event,
        system_event,
    ]


def test_unsubscribe_removes_filtered_subscription():
    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        handler,
        event_types={"USER_ADDED"},
    )

    assert bus.unsubscribe(handler) is True

    bus.publish(make_event("USER_ADDED"))

    assert received == []


def test_duplicate_handler_with_different_filters_is_not_allowed():
    bus = OrganizationEventBus()

    def handler(event):
        pass

    bus.subscribe(
        handler,
        event_types={"USER_ADDED"},
    )

    bus.subscribe(
        handler,
        event_types={"SYSTEM_ADDED"},
    )

    assert bus.subscriber_count() == 1