from datetime import datetime, timezone

import pytest

from yoma.office.operations.model import OperationalEvent
from yoma.office.operations.situation import OperationalSituation
from yoma.office.operations.model import OperationalSignal
from yoma.office.operational_event_persistence import OperationalEventPersistence
from yoma.office.operational_signal_persistence import OperationalSignalPersistence
from yoma.office.operational_situation_persistence import OperationalSituationPersistence


def event(event_id="evt-1", occurred_at=None, organization_id="org-1"):
    return OperationalEvent(
        event_id=event_id,
        event_type="test.event",
        occurred_at=occurred_at or datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id="user-1",
        system_id="system-1",
        source="test",
        location_id=None,
        severity="info",
        data={"value": 1},
    )


def signal(signal_id="sig-1", detected_at=None, organization_id="org-1"):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type="test.signal",
        detected_at=detected_at or datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id="user-1",
        system_id="system-1",
        score=0.8,
        severity="warning",
        evidence_event_ids=("evt-1",),
        data={"value": 2},
    )


def situation(situation_id="sit-1", detected_at=None, organization_id="org-1"):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="test.situation",
        detected_at=detected_at or datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id="user-1",
        system_id="system-1",
        severity="warning",
        score=0.9,
        signal_ids=("sig-1",),
        evidence_event_ids=("evt-1",),
        data={"value": 3},
    )


def test_event_duplicate_is_idempotent(tmp_path):
    store = OperationalEventPersistence(tmp_path / "test.db")

    assert store.save(event()) is True
    assert store.save(event()) is False
    assert store.count() == 1


def test_signal_duplicate_is_idempotent(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "test.db")

    assert store.save(signal()) is True
    assert store.save(signal()) is False
    assert store.count() == 1


def test_situation_duplicate_is_idempotent(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "test.db")

    assert store.save(situation()) is True
    assert store.save(situation()) is False
    assert store.count() == 1


def test_event_restart_preserves_data(tmp_path):
    db = tmp_path / "restart.db"

    first = OperationalEventPersistence(db)
    first.save(event("evt-restart"))

    second = OperationalEventPersistence(db)

    restored = second.get("evt-restart")

    assert restored is not None
    assert restored.event_id == "evt-restart"
    assert restored.data == {"value": 1}


def test_signal_restart_preserves_data(tmp_path):
    db = tmp_path / "restart.db"

    first = OperationalSignalPersistence(db)
    first.save(signal("sig-restart"))

    second = OperationalSignalPersistence(db)

    restored = second.get("sig-restart")

    assert restored is not None
    assert restored.signal_id == "sig-restart"
    assert restored.data == {"value": 2}


def test_situation_restart_preserves_data(tmp_path):
    db = tmp_path / "restart.db"

    first = OperationalSituationPersistence(db)
    first.save(situation("sit-restart"))

    second = OperationalSituationPersistence(db)

    restored = second.get("sit-restart")

    assert restored is not None
    assert restored.situation_id == "sit-restart"
    assert restored.data == {"value": 3}


def test_event_json_payload_round_trip(tmp_path):
    store = OperationalEventPersistence(tmp_path / "test.db")

    original = event()
    original.data.update(
        {
            "nested": {
                "enabled": True,
                "count": 4,
            },
            "items": [1, 2, 3],
        }
    )

    store.save(original)

    restored = store.get(original.event_id)

    assert restored is not None
    assert restored.data == original.data


def test_signal_json_payload_round_trip(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "test.db")

    original = signal()
    original.data.update(
        {
            "nested": {
                "enabled": True,
                "count": 4,
            },
            "items": [1, 2, 3],
        }
    )

    store.save(original)

    restored = store.get(original.signal_id)

    assert restored is not None
    assert restored.data == original.data


def test_situation_json_payload_round_trip(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "test.db")

    original = situation()
    original.data.update(
        {
            "nested": {
                "enabled": True,
                "count": 4,
            },
            "items": [1, 2, 3],
        }
    )

    store.save(original)

    restored = store.get(original.situation_id)

    assert restored is not None
    assert restored.data == original.data


def test_event_identity_scope_is_isolated(tmp_path):
    store = OperationalEventPersistence(tmp_path / "test.db")

    store.save(event("evt-a", organization_id="org-a"))
    store.save(event("evt-b", organization_id="org-b"))

    assert len(store.by_organization("org-a")) == 1
    assert len(store.by_organization("org-b")) == 1


def test_signal_identity_scope_is_isolated(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "test.db")

    store.save(signal("sig-a", organization_id="org-a"))
    store.save(signal("sig-b", organization_id="org-b"))

    assert len(store.by_organization("org-a")) == 1
    assert len(store.by_organization("org-b")) == 1


def test_situation_identity_scope_is_isolated(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "test.db")

    store.save(situation("sit-a", organization_id="org-a"))
    store.save(situation("sit-b", organization_id="org-b"))

    assert len(store.by_organization("org-a")) == 1
    assert len(store.by_organization("org-b")) == 1


def test_event_between_is_inclusive(tmp_path):
    store = OperationalEventPersistence(tmp_path / "test.db")

    first = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    last = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    store.save(event("a", first))
    store.save(event("b", first.replace(hour=11)))
    store.save(event("c", last))

    result = store.between(first, last)

    assert [item.event_id for item in result] == ["a", "b", "c"]


def test_signal_between_is_inclusive(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "test.db")

    first = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    last = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    store.save(signal("a", first))
    store.save(signal("b", first.replace(hour=11)))
    store.save(signal("c", last))

    result = store.between(first, last)

    assert [item.signal_id for item in result] == ["a", "b", "c"]


def test_situation_between_is_inclusive(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "test.db")

    first = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    last = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    store.save(situation("a", first))
    store.save(situation("b", first.replace(hour=11)))
    store.save(situation("c", last))

    result = store.between(first, last)

    assert [item.situation_id for item in result] == ["a", "b", "c"]


def test_event_ordering_is_deterministic(tmp_path):
    store = OperationalEventPersistence(tmp_path / "test.db")

    timestamp = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(event("b", timestamp))
    store.save(event("a", timestamp))

    result = store.load_all()

    assert [item.event_id for item in result] == ["a", "b"]


def test_signal_ordering_is_deterministic(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "test.db")

    timestamp = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(signal("b", timestamp))
    store.save(signal("a", timestamp))

    result = store.load_all()

    assert [item.signal_id for item in result] == ["a", "b"]


def test_situation_ordering_is_deterministic(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "test.db")

    timestamp = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(situation("b", timestamp))
    store.save(situation("a", timestamp))

    result = store.load_all()

    assert [item.situation_id for item in result] == ["a", "b"]


def test_event_missing_id_returns_none(tmp_path):
    store = OperationalEventPersistence(tmp_path / "test.db")

    assert store.get("missing") is None


def test_signal_missing_id_returns_none(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "test.db")

    assert store.get("missing") is None


def test_situation_missing_id_returns_none(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "test.db")

    assert store.get("missing") is None


def test_event_clear_is_durable(tmp_path):
    db = tmp_path / "clear.db"

    store = OperationalEventPersistence(db)
    store.save(event())
    store.clear()

    restored = OperationalEventPersistence(db)

    assert restored.count() == 0


def test_signal_clear_is_durable(tmp_path):
    db = tmp_path / "clear.db"

    store = OperationalSignalPersistence(db)
    store.save(signal())
    store.clear()

    restored = OperationalSignalPersistence(db)

    assert restored.count() == 0


def test_situation_clear_is_durable(tmp_path):
    db = tmp_path / "clear.db"

    store = OperationalSituationPersistence(db)
    store.save(situation())
    store.clear()

    restored = OperationalSituationPersistence(db)

    assert restored.count() == 0


def test_bulk_save_preserves_all_records(tmp_path):
    store = OperationalEventPersistence(tmp_path / "bulk.db")

    records = [
        event(f"evt-{index}")
        for index in range(10)
    ]

    assert store.save_many(records) == 10
    assert store.count() == 10


def test_signal_bulk_save_preserves_all_records(tmp_path):
    store = OperationalSignalPersistence(tmp_path / "bulk.db")

    records = [
        signal(f"sig-{index}")
        for index in range(10)
    ]

    assert store.save_many(records) == 10
    assert store.count() == 10


def test_situation_bulk_save_preserves_all_records(tmp_path):
    store = OperationalSituationPersistence(tmp_path / "bulk.db")

    records = [
        situation(f"sit-{index}")
        for index in range(10)
    ]

    assert store.save_many(records) == 10
    assert store.count() == 10
