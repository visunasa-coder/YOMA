from __future__ import annotations

import pytest

from yoma.office.central_server import CentralServerAdapter
from yoma.office.organization_events import OrganizationChangeEventStore


def make_adapter():
    return CentralServerAdapter(name="central-server")


def test_adapter_has_change_event_store():
    adapter = make_adapter()

    assert isinstance(
        adapter.change_events,
        OrganizationChangeEventStore,
    )


def test_initial_user_reconciliation_creates_added_events():
    adapter = make_adapter()

    result = adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            },
            {
                "id": "u2",
                "name": "Bob",
            },
        ]
    )

    assert result["added"] == ["u1", "u2"]

    events = adapter.change_events.by_type("USER_ADDED")

    assert len(events) == 2
    assert [event.entity_id for event in events] == ["u1", "u2"]


def test_added_user_creates_user_added_event():
    adapter = make_adapter()

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            },
            {
                "id": "u2",
                "name": "Bob",
            },
        ]
    )

    events = adapter.change_events.by_type("USER_ADDED")

    assert len(events) == 2
    assert events[-1].entity_id == "u2"


def test_removed_user_creates_user_removed_event():
    adapter = make_adapter()

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            },
            {
                "id": "u2",
                "name": "Bob",
            },
        ]
    )

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    events = adapter.change_events.by_type("USER_REMOVED")

    assert len(events) == 1
    assert events[0].entity_id == "u2"


def test_updated_user_creates_user_updated_event():
    adapter = make_adapter()

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

    events = adapter.change_events.by_type("USER_UPDATED")

    assert len(events) == 1
    assert events[0].entity_id == "u1"
    assert events[0].previous_state["department"] == "HR"
    assert events[0].current_state["department"] == "Finance"


def test_user_reactivation_creates_user_activated_event():
    adapter = make_adapter()

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

    events = adapter.change_events.by_type("USER_ACTIVATED")

    assert len(events) == 1
    assert events[0].entity_id == "u1"


def test_user_deactivation_creates_user_deactivated_event():
    adapter = make_adapter()

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

    events = adapter.change_events.by_type("USER_DEACTIVATED")

    assert len(events) == 1
    assert events[0].entity_id == "u1"


def test_system_added_creates_system_added_event():
    adapter = make_adapter()

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
            }
        ]
    )

    events = adapter.change_events.by_type("SYSTEM_ADDED")

    assert len(events) == 1
    assert events[0].entity_id == "s1"


def test_system_removed_creates_system_removed_event():
    adapter = make_adapter()

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
            },
            {
                "id": "s2",
                "name": "Workstation 2",
            },
        ]
    )

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
            }
        ]
    )

    events = adapter.change_events.by_type("SYSTEM_REMOVED")

    assert len(events) == 1
    assert events[0].entity_id == "s2"


def test_system_updated_creates_system_updated_event():
    adapter = make_adapter()

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

    events = adapter.change_events.by_type("SYSTEM_UPDATED")

    assert len(events) == 1
    assert events[0].entity_id == "s1"
    assert events[0].previous_state["name"] == "Old Name"
    assert events[0].current_state["name"] == "New Name"


def test_invalid_user_reconciliation_creates_no_event():
    adapter = make_adapter()

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

    assert adapter.change_events.count() == 1


def test_invalid_system_reconciliation_creates_no_event():
    adapter = make_adapter()

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

    assert adapter.change_events.count() == 1