from __future__ import annotations

from pathlib import Path

from yoma.office.central_server import CentralServerAdapter
from yoma.office.organization_event_persistence import (
    OrganizationChangeEventPersistence,
)


def make_adapter(
    db_path: Path | None = None,
) -> CentralServerAdapter:
    if db_path is None:
        return CentralServerAdapter(
            name="central-server"
        )

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    return CentralServerAdapter(
        name="central-server",
        event_persistence=persistence,
    )


def test_adapter_accepts_event_persistence(tmp_path: Path):
    adapter = make_adapter(
        tmp_path / "events.db"
    )

    assert adapter.event_persistence is not None


def test_user_event_is_persisted(tmp_path: Path):
    db_path = tmp_path / "events.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    events = persistence.load_all()

    assert len(events) == 1
    assert events[0].event_type == "USER_ADDED"
    assert events[0].entity_id == "u1"


def test_system_event_is_persisted(tmp_path: Path):
    db_path = tmp_path / "events.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_systems(
        [
            {
                "id": "s1",
                "name": "Workstation 1",
            }
        ]
    )

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    events = persistence.load_all()

    assert len(events) == 1
    assert events[0].event_type == "SYSTEM_ADDED"
    assert events[0].entity_id == "s1"


def test_multiple_changes_are_persisted_in_order(
    tmp_path: Path,
):
    db_path = tmp_path / "events.db"

    adapter = make_adapter(db_path)

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
                "name": "Alice Updated",
            }
        ]
    )

    adapter.reconcile_users([])

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    events = persistence.load_all()

    assert [
        event.event_type
        for event in events
    ] == [
        "USER_ADDED",
        "USER_UPDATED",
        "USER_REMOVED",
    ]


def test_persisted_event_survives_new_adapter(
    tmp_path: Path,
):
    db_path = tmp_path / "events.db"

    first = make_adapter(db_path)

    first.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    second = make_adapter(db_path)

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    events = persistence.load_all()

    assert len(events) == 1
    assert events[0].entity_id == "u1"

    assert second.event_persistence is not None


def test_event_bus_and_persistence_receive_same_event(
    tmp_path: Path,
):
    db_path = tmp_path / "events.db"

    adapter = make_adapter(db_path)

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

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    persisted = persistence.load_all()

    assert len(received) == 1
    assert len(persisted) == 1
    assert received[0] == persisted[0]


def test_invalid_reconciliation_persists_no_new_event(
    tmp_path: Path,
):
    db_path = tmp_path / "events.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    try:
        adapter.reconcile_users(
            [
                {
                    "name": "Invalid",
                }
            ]
        )
    except ValueError:
        pass

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    events = persistence.load_all()

    assert len(events) == 1


def test_persistence_is_optional(tmp_path: Path):
    adapter = CentralServerAdapter(
        name="central-server"
    )

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    assert adapter.change_events.count() == 1
    assert adapter.event_persistence is None


def test_existing_event_store_remains_available(
    tmp_path: Path,
):
    db_path = tmp_path / "events.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [
            {
                "id": "u1",
                "name": "Alice",
            }
        ]
    )

    assert adapter.change_events.count() == 1

    persistence = OrganizationChangeEventPersistence(
        db_path
    )

    assert persistence.count() == 1