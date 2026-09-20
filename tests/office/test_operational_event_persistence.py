from datetime import datetime, timezone

import pytest

from yoma.office.operational_event_persistence import (
    OperationalEventPersistence,
)
from yoma.office.operations import OperationalEvent


def make_event(
    event_id: str = "evt-1",
    *,
    occurred_at: datetime | None = None,
    organization_id: str | None = "org-1",
    user_id: str | None = "user-1",
    system_id: str | None = "system-1",
    event_type: str = "workload.high",
) -> OperationalEvent:
    return OperationalEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at
        or datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        source="test",
        location_id="loc-1",
        severity="warning",
        data={"score": 0.9, "value": event_id},
    )


def test_initializes_database(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    assert persistence.count() == 0


def test_save_and_get_round_trip(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")
    event = make_event()

    assert persistence.save(event) is True
    assert persistence.get("evt-1") == event


def test_duplicate_event_id_is_ignored(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")
    event = make_event()

    assert persistence.save(event) is True
    assert persistence.save(event) is False
    assert persistence.count() == 1


def test_save_many_returns_inserted_count(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    events = [
        make_event("evt-1"),
        make_event("evt-2"),
        make_event("evt-3"),
    ]

    assert persistence.save_many(events) == 3
    assert persistence.save_many(events) == 0
    assert persistence.count() == 3


def test_load_all_is_chronological_and_deterministic(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    later = make_event(
        "evt-b",
        occurred_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
    )
    earlier = make_event(
        "evt-a",
        occurred_at=datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
    )

    persistence.save_many([later, earlier])

    assert persistence.load_all() == [earlier, later]


def test_filter_by_type(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    persistence.save(make_event("evt-1", event_type="workload.high"))
    persistence.save(make_event("evt-2", event_type="meeting_load.high"))

    result = persistence.by_type("workload.high")

    assert [event.event_id for event in result] == ["evt-1"]


def test_filter_by_organization_user_and_system(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    persistence.save(
        make_event(
            "evt-org",
            organization_id="org-a",
            user_id="user-a",
            system_id="system-a",
        )
    )
    persistence.save(
        make_event(
            "evt-other",
            organization_id="org-b",
            user_id="user-b",
            system_id="system-b",
        )
    )

    assert [e.event_id for e in persistence.by_organization("org-a")] == [
        "evt-org"
    ]
    assert [e.event_id for e in persistence.by_user("user-a")] == [
        "evt-org"
    ]
    assert [e.event_id for e in persistence.by_system("system-a")] == [
        "evt-org"
    ]


def test_between_is_inclusive(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    start = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)
    middle = datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)

    persistence.save(make_event("evt-start", occurred_at=start))
    persistence.save(make_event("evt-middle", occurred_at=middle))
    persistence.save(make_event("evt-end", occurred_at=end))

    result = persistence.between(start, end)

    assert [event.event_id for event in result] == [
        "evt-start",
        "evt-middle",
        "evt-end",
    ]


def test_clear_removes_history(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    persistence.save(make_event())

    persistence.clear()

    assert persistence.count() == 0
    assert persistence.get("evt-1") is None


def test_invalid_event_is_rejected(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    with pytest.raises(TypeError, match="OperationalEvent"):
        persistence.save("not-an-event")  # type: ignore[arg-type]


def test_invalid_filters_are_rejected(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    with pytest.raises(ValueError, match="event_type"):
        persistence.by_type("")

    with pytest.raises(ValueError, match="organization_id"):
        persistence.by_organization("")

    with pytest.raises(ValueError, match="user_id"):
        persistence.by_user("")

    with pytest.raises(ValueError, match="system_id"):
        persistence.by_system("")


def test_invalid_time_range_is_rejected(tmp_path):
    persistence = OperationalEventPersistence(tmp_path / "events.db")

    start = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="start"):
        persistence.between(start, end)


def test_restart_recovers_persisted_events(tmp_path):
    db_path = tmp_path / "events.db"

    first = OperationalEventPersistence(db_path)
    event = make_event()
    first.save(event)

    second = OperationalEventPersistence(db_path)

    assert second.count() == 1
    assert second.get(event.event_id) == event
