from __future__ import annotations

import pytest

from yoma.office.central_server import CentralServerAdapter
from yoma.office.organization_event_bus import OrganizationEventBus


def make_adapter():
    return CentralServerAdapter(name="central-server")


def test_adapter_has_event_bus():
    adapter = make_adapter()

    assert isinstance(
        adapter.event_bus,
        OrganizationEventBus,
    )


def test_user_added_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    assert len(received) == 1
    assert received[0].event_type == "USER_ADDED"
    assert received[0].entity_type == "user"
    assert received[0].entity_id == "u1"


def test_user_removed_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    adapter.reconcile_users([])

    events = [
        event
        for event in received
        if event.event_type == "USER_REMOVED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "u1"


def test_user_updated_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
                "department": "HR",
            }
        ]
    )

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
                "department": "Finance",
            }
        ]
    )

    events = [
        event
        for event in received
        if event.event_type == "USER_UPDATED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "u1"
    assert events[0].previous_state["department"] == "HR"
    assert events[0].current_state["department"] == "Finance"


def test_user_activation_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
                "active": False,
            }
        ]
    )

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
                "active": True,
            }
        ]
    )

    events = [
        event
        for event in received
        if event.event_type == "USER_ACTIVATED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "u1"


def test_user_deactivation_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
                "active": True,
            }
        ]
    )

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
                "active": False,
            }
        ]
    )

    events = [
        event
        for event in received
        if event.event_type == "USER_DEACTIVATED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "u1"


def test_system_added_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
            }
        ]
    )

    assert len(received) == 1
    assert received[0].event_type == "SYSTEM_ADDED"
    assert received[0].entity_type == "system"
    assert received[0].entity_id == "s1"


def test_system_removed_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
            }
        ]
    )

    adapter.reconcile_systems([])

    events = [
        event
        for event in received
        if event.event_type == "SYSTEM_REMOVED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "s1"


def test_system_updated_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Old Name",
            }
        ]
    )

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "New Name",
            }
        ]
    )

    events = [
        event
        for event in received
        if event.event_type == "SYSTEM_UPDATED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "s1"
    assert events[0].previous_state["name"] == "Old Name"
    assert events[0].current_state["name"] == "New Name"


def test_system_activation_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
                "active": False,
            }
        ]
    )

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
                "active": True,
            }
        ]
    )

    events = [
        event
        for event in received
        if event.event_type == "SYSTEM_ACTIVATED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "s1"


def test_system_deactivation_is_published_to_event_bus():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
                "active": True,
            }
        ]
    )

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
                "active": False,
            }
        ]
    )

    events = [
        event
        for event in received
        if event.event_type == "SYSTEM_DEACTIVATED"
    ]

    assert len(events) == 1
    assert events[0].entity_id == "s1"


def test_event_store_and_event_bus_receive_same_event():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    stored = adapter.change_events.events()

    assert len(stored) == 1
    assert len(received) == 1
    assert stored[0] == received[0]


def test_invalid_user_reconciliation_publishes_no_event():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    with pytest.raises(ValueError):
        adapter.reconcile_users(
            [
                {
                    "name": "Invalid",
                }
            ]
        )

    assert len(received) == 1


def test_invalid_system_reconciliation_publishes_no_event():
    adapter = make_adapter()
    received = []

    def handler(event):
        received.append(event)

    adapter.event_bus.subscribe(handler)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "System 1",
            }
        ]
    )

    with pytest.raises(ValueError):
        adapter.reconcile_systems(
            [
                {
                    "name": "Invalid",
                }
            ]
        )

    assert len(received) == 1