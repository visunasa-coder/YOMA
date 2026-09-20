from yoma.office.central_server import CentralServerAdapter
from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_event_persistence import (
    OrganizationChangeEventPersistence,
)
from yoma.office.organization_events import OrganizationChangeEvent


def test_persisted_events_can_be_replayed(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    event = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
        current_state={"user_id": "u1", "name": "Vishal"},
    )

    persistence.save(event)

    bus = OrganizationEventBus()
    received = []

    bus.subscribe(lambda received_event: received.append(received_event))

    deliveries = persistence.replay(bus)

    assert deliveries == 1
    assert len(received) == 1
    assert received[0] == event


def test_replay_preserves_persisted_event_order(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    events = [
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="user",
            entity_id="u1",
        ),
        OrganizationChangeEvent(
            event_type="USER_UPDATED",
            entity_type="user",
            entity_id="u1",
        ),
        OrganizationChangeEvent(
            event_type="USER_DEACTIVATED",
            entity_type="user",
            entity_id="u1",
        ),
    ]

    for event in events:
        persistence.save(event)

    bus = OrganizationEventBus()
    received = []

    bus.subscribe(lambda received_event: received.append(received_event))

    persistence.replay(bus)

    assert received == events


def test_replay_uses_event_bus_filtering(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    persistence.save(
        OrganizationChangeEvent(
            event_type="USER_ADDED",
            entity_type="user",
            entity_id="u1",
        )
    )
    persistence.save(
        OrganizationChangeEvent(
            event_type="SYSTEM_ADDED",
            entity_type="system",
            entity_id="s1",
        )
    )

    users = []
    systems = []

    bus = OrganizationEventBus()

    bus.subscribe(
        lambda event: users.append(event),
        entity_types={"user"},
    )
    bus.subscribe(
        lambda event: systems.append(event),
        entity_types={"system"},
    )

    persistence.replay(bus)

    assert len(users) == 1
    assert users[0].entity_id == "u1"

    assert len(systems) == 1
    assert systems[0].entity_id == "s1"


def test_empty_persistence_replay_is_safe(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    bus = OrganizationEventBus()

    assert persistence.replay(bus) == 0


def test_replay_rejects_invalid_event_bus(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    try:
        persistence.replay(object())
    except TypeError as exc:
        assert "OrganizationEventBus" in str(exc)
    else:
        raise AssertionError("Expected TypeError")