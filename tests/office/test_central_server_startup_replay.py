from yoma.office.central_server import CentralServerAdapter
from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_event_persistence import (
    OrganizationChangeEventPersistence,
)
from yoma.office.organization_events import OrganizationChangeEvent


def test_central_server_accepts_event_persistence(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    assert adapter.event_persistence is persistence


def test_central_server_replays_persisted_events(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    event = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
        current_state={"user_id": "u1", "name": "Vishal"},
    )

    persistence.save(event)

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    received = []
    adapter.event_bus.subscribe(
        lambda received_event: received.append(received_event)
    )

    deliveries = adapter.replay_events()

    assert deliveries == 1
    assert received == [event]


def test_central_server_replay_preserves_event_order(tmp_path):
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

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    received = []
    adapter.event_bus.subscribe(
        lambda received_event: received.append(received_event)
    )

    adapter.replay_events()

    assert received == events


def test_central_server_replay_uses_existing_event_bus_filters(tmp_path):
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

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    users = []
    systems = []

    adapter.event_bus.subscribe(
        lambda event: users.append(event),
        entity_types={"user"},
    )
    adapter.event_bus.subscribe(
        lambda event: systems.append(event),
        entity_types={"system"},
    )

    adapter.replay_events()

    assert len(users) == 1
    assert users[0].entity_id == "u1"

    assert len(systems) == 1
    assert systems[0].entity_id == "s1"


def test_central_server_replay_without_persistence_is_safe():
    adapter = CentralServerAdapter(name="central")

    assert adapter.replay_events() == 0


def test_central_server_replay_empty_persistence_is_safe(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    assert adapter.replay_events() == 0


def test_central_server_replay_does_not_duplicate_event_store(tmp_path):
    persistence = OrganizationChangeEventPersistence(tmp_path / "events.db")

    event = OrganizationChangeEvent(
        event_type="USER_ADDED",
        entity_type="user",
        entity_id="u1",
    )

    persistence.save(event)

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    assert adapter.change_events.count() == 0

    adapter.replay_events()

    # Replay delivers historical events through the bus,
    # but does not duplicate them into the in-memory event store.
    assert adapter.change_events.count() == 0


def test_central_server_replay_returns_delivery_count(tmp_path):
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

    adapter = CentralServerAdapter(
        name="central",
        event_persistence=persistence,
    )

    deliveries = adapter.replay_events()

    assert deliveries == 0