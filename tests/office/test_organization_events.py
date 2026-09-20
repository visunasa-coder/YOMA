from __future__ import annotations

import pytest

from yoma.office.organization_events import (
    OrganizationChangeEvent,
    OrganizationChangeEventStore,
)


def test_event_requires_event_type():
    with pytest.raises(ValueError):
        OrganizationChangeEvent(
            event_type="",
            entity_type="user",
            entity_id="u1",
        )


def test_event_requires_entity_type():
    with pytest.raises(ValueError):
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="",
            entity_id="u1",
        )


def test_event_requires_entity_id():
    with pytest.raises(ValueError):
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="user",
            entity_id="",
        )


def test_event_stores_core_identity():
    event = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
    )

    assert event.event_type == "USER_ADDED"
    assert event.entity_type == "user"
    assert event.entity_id == "u1"


def test_event_supports_previous_and_current_state():
    event = OrganizationChangeEvent(
        event_type="USER_UPDATED",
        entity_type="user",
        entity_id="u1",
        previous_state={"name": "Old"},
        current_state={"name": "New"},
    )

    assert event.previous_state == {"name": "Old"}
    assert event.current_state == {"name": "New"}


def test_event_supports_metadata():
    event = OrganizationChangeEvent(
        event_type="SYSTEM_ADDED",
        entity_type="system",
        entity_id="s1",
        metadata={"source": "central_server"},
    )

    assert event.metadata == {"source": "central_server"}


def test_event_timestamp_is_generated():
    event = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
    )

    assert event.timestamp
    assert isinstance(event.timestamp, str)


def test_event_store_starts_empty():
    store = OrganizationChangeEventStore()

    assert store.events() == []
    assert store.count() == 0


def test_store_adds_event():
    store = OrganizationChangeEventStore()

    event = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
    )

    store.add(event)

    assert store.count() == 1
    assert store.events() == [event]


def test_store_preserves_event_order():
    store = OrganizationChangeEventStore()

    first = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
    )

    second = OrganizationChangeEvent(
        event_type="USER_UPDATED",
        entity_type="user",
        entity_id="u1",
    )

    store.add(first)
    store.add(second)

    assert store.events() == [first, second]


def test_store_rejects_invalid_event():
    store = OrganizationChangeEventStore()

    with pytest.raises(TypeError):
        store.add("invalid")


def test_store_filters_by_event_type():
    store = OrganizationChangeEventStore()

    store.add(
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="user",
            entity_id="u1",
        )
    )

    store.add(
        OrganizationChangeEvent(
            event_type="USER_UPDATED",
            entity_type="user",
            entity_id="u1",
        )
    )

    store.add(
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="user",
            entity_id="u2",
        )
    )

    events = store.by_type("USER_ADDED")

    assert len(events) == 2
    assert [event.entity_id for event in events] == ["u1", "u2"]


def test_store_filters_by_entity():
    store = OrganizationChangeEventStore()

    store.add(
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="user",
            entity_id="u1",
        )
    )

    store.add(
        OrganizationChangeEvent(
            event_type="USER_UPDATED",
            entity_type="user",
            entity_id="u2",
        )
    )

    events = store.by_entity("user", "u1")

    assert len(events) == 1
    assert events[0].entity_id == "u1"


def test_store_rejects_invalid_filter():
    store = OrganizationChangeEventStore()

    with pytest.raises(ValueError):
        store.by_entity("", "u1")

    with pytest.raises(ValueError):
        store.by_entity("user", "")