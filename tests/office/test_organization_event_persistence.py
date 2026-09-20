from __future__ import annotations

from pathlib import Path

import pytest

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


def test_event_persistence_requires_db_path():
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    with pytest.raises(ValueError):
        OrganizationChangeEventPersistence("")


def test_event_persistence_creates_storage(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    db_path = tmp_path / "events.db"

    persistence = OrganizationChangeEventPersistence(db_path)

    assert db_path.exists()
    assert persistence.count() == 0


def test_save_event(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    event = make_event()

    persistence.save(event)

    assert persistence.count() == 1


def test_load_events_preserves_event(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    event = OrganizationChangeEvent(
        event_type="USER_UPDATED",
        entity_type="user",
        entity_id="u1",
        previous_state={"name": "Alice"},
        current_state={"name": "Bob"},
        metadata={"source": "central_server"},
    )

    persistence.save(event)

    loaded = persistence.load_all()

    assert len(loaded) == 1
    assert loaded[0].event_type == "USER_UPDATED"
    assert loaded[0].entity_type == "user"
    assert loaded[0].entity_id == "u1"
    assert loaded[0].previous_state == {"name": "Alice"}
    assert loaded[0].current_state == {"name": "Bob"}
    assert loaded[0].metadata == {
        "source": "central_server"
    }
    assert loaded[0].timestamp == event.timestamp


def test_events_preserve_insertion_order(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

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

    persistence.save(first)
    persistence.save(second)
    persistence.save(third)

    loaded = persistence.load_all()

    assert loaded == [
        first,
        second,
        third,
    ]


def test_duplicate_event_is_not_saved_twice(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    event = make_event()

    persistence.save(event)
    persistence.save(event)

    assert persistence.count() == 1


def test_load_empty_returns_empty_list(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    assert persistence.load_all() == []


def test_persistence_survives_new_instance(tmp_path: Path):
    db_path = tmp_path / "events.db"

    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    first = OrganizationChangeEventPersistence(db_path)

    event = make_event(
        event_type="SYSTEM_ADDED",
        entity_type="system",
        entity_id="s1",
    )

    first.save(event)

    second = OrganizationChangeEventPersistence(db_path)

    loaded = second.load_all()

    assert loaded == [event]


def test_load_by_event_type(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    persistence.save(
        make_event("USER_ADDED", "user", "u1")
    )

    persistence.save(
        make_event("USER_UPDATED", "user", "u1")
    )

    persistence.save(
        make_event("USER_ADDED", "user", "u2")
    )

    loaded = persistence.by_type("USER_ADDED")

    assert len(loaded) == 2
    assert [
        event.entity_id
        for event in loaded
    ] == ["u1", "u2"]


def test_load_by_entity(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    persistence.save(
        make_event("USER_ADDED", "user", "u1")
    )

    persistence.save(
        make_event("USER_UPDATED", "user", "u2")
    )

    persistence.save(
        make_event("USER_REMOVED", "user", "u1")
    )

    loaded = persistence.by_entity(
        "user",
        "u1",
    )

    assert len(loaded) == 2
    assert [
        event.event_type
        for event in loaded
    ] == [
        "USER_ADDED",
        "USER_REMOVED",
    ]


def test_invalid_event_cannot_be_saved(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    with pytest.raises(TypeError):
        persistence.save("invalid")


def test_invalid_event_type_filter_is_rejected(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    with pytest.raises(ValueError):
        persistence.by_type("")


def test_invalid_entity_filter_is_rejected(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    with pytest.raises(ValueError):
        persistence.by_entity(
            "",
            "u1",
        )

    with pytest.raises(ValueError):
        persistence.by_entity(
            "user",
            "",
        )


def test_clear_removes_all_events(tmp_path: Path):
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    persistence.save(make_event())

    assert persistence.count() == 1

    persistence.clear()

    assert persistence.count() == 0
    assert persistence.load_all() == []


def test_replay_publishes_persisted_events(tmp_path: Path):
    from yoma.office.organization_event_bus import OrganizationEventBus
    from yoma.office.organization_event_persistence import (
        OrganizationChangeEventPersistence,
    )

    persistence = OrganizationChangeEventPersistence(
        tmp_path / "events.db"
    )

    first = make_event(
        "USER_ADDED",
        "user",
        "u1",
    )

    second = make_event(
        "USER_UPDATED",
        "user",
        "u1",
    )

    persistence.save(first)
    persistence.save(second)

    bus = OrganizationEventBus()
    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)

    delivered = persistence.replay(bus)

    assert delivered == 2
    assert received == [
        first,
        second,
    ]