from datetime import datetime, timedelta

import pytest

from yoma.office.operational_event_persistence import OperationalEventPersistence
from yoma.office.operational_signal_persistence import OperationalSignalPersistence
from yoma.office.operational_situation_persistence import (
    OperationalSituationPersistence,
)
from yoma.office.operational_timeline import (
    OperationalTimeline,
    OperationalTimelineEntry,
)
from yoma.office.operations import (
    OperationalEvent,
    OperationalSignal,
    OperationalSituation,
)


def make_event(
    event_id="E1",
    occurred_at=None,
    organization_id="ORG-1",
    user_id="U1",
    system_id="SYS-1",
):
    return OperationalEvent(
        event_id=event_id,
        event_type="work.started",
        occurred_at=occurred_at or datetime(2026, 1, 1, 9, 0),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        source="test",
        severity="info",
        data={"value": event_id},
    )


def make_signal(
    signal_id="S1",
    detected_at=None,
    organization_id="ORG-1",
    user_id="U1",
    system_id="SYS-1",
    evidence=("E1",),
):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type="workload.high",
        detected_at=detected_at or datetime(2026, 1, 1, 9, 5),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        score=0.9,
        severity="high",
        evidence_event_ids=evidence,
        data={"value": signal_id},
    )


def make_situation(
    situation_id="SIT-1",
    detected_at=None,
    organization_id="ORG-1",
    user_id="U1",
    system_id="SYS-1",
    signal_ids=("S1",),
    evidence=("E1",),
):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=detected_at or datetime(2026, 1, 1, 9, 10),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        severity="high",
        score=0.9,
        signal_ids=signal_ids,
        evidence_event_ids=evidence,
        data={"value": situation_id},
    )


@pytest.fixture
def stores(tmp_path):
    db = tmp_path / "timeline.db"

    return (
        OperationalEventPersistence(db),
        OperationalSignalPersistence(db),
        OperationalSituationPersistence(db),
    )


@pytest.fixture
def timeline(stores):
    return OperationalTimeline(*stores)


def test_constructor_rejects_invalid_stores():
    with pytest.raises(TypeError):
        OperationalTimeline(None, None, None)


def test_empty_timeline(timeline):
    assert timeline.load_all() == []
    assert timeline.count() == 0


def test_unifies_all_artifact_types(stores, timeline):
    events, signals, situations = stores

    events.save(make_event())
    signals.save(make_signal())
    situations.save(make_situation())

    entries = timeline.load_all()

    assert [entry.entry_type for entry in entries] == [
        "event",
        "signal",
        "situation",
    ]
    assert [entry.entry_id for entry in entries] == [
        "E1",
        "S1",
        "SIT-1",
    ]
    assert all(isinstance(entry, OperationalTimelineEntry) for entry in entries)


def test_chronological_order_is_deterministic(stores, timeline):
    events, signals, situations = stores
    timestamp = datetime(2026, 1, 1, 10, 0)

    events.save(make_event("E2", timestamp))
    events.save(make_event("E1", timestamp))
    signals.save(make_signal("S2", timestamp))
    signals.save(make_signal("S1", timestamp))
    situations.save(make_situation("SIT-2", timestamp))
    situations.save(make_situation("SIT-1", timestamp))

    entries = timeline.load_all()

    assert [
        (entry.occurred_at, entry.entry_type, entry.entry_id)
        for entry in entries
    ] == [
        (timestamp, "event", "E1"),
        (timestamp, "event", "E2"),
        (timestamp, "signal", "S1"),
        (timestamp, "signal", "S2"),
        (timestamp, "situation", "SIT-1"),
        (timestamp, "situation", "SIT-2"),
    ]


def test_count(timeline, stores):
    events, signals, situations = stores

    events.save_many([make_event("E1"), make_event("E2")])
    signals.save_many([make_signal("S1"), make_signal("S2")])
    situations.save(make_situation())

    assert timeline.count() == 5


def test_by_type(timeline, stores):
    events, signals, situations = stores

    events.save(make_event())
    signals.save(make_signal())
    situations.save(make_situation())

    assert [x.entry_id for x in timeline.by_type("event")] == ["E1"]
    assert [x.entry_id for x in timeline.by_type("SIGNAL")] == ["S1"]
    assert [x.entry_id for x in timeline.by_type("situation")] == ["SIT-1"]


def test_by_type_rejects_unknown_type(timeline):
    with pytest.raises(ValueError):
        timeline.by_type("unknown")


def test_by_organization(timeline, stores):
    events, signals, situations = stores

    events.save(make_event("E1", organization_id="ORG-1"))
    events.save(make_event("E2", organization_id="ORG-2"))
    signals.save(make_signal("S1", organization_id="ORG-1"))
    situations.save(make_situation("SIT-2", organization_id="ORG-2"))

    assert [
        x.entry_id for x in timeline.by_organization("ORG-1")
    ] == ["E1", "S1"]


def test_by_user(timeline, stores):
    events, signals, situations = stores

    events.save(make_event("E1", user_id="U1"))
    events.save(make_event("E2", user_id="U2"))
    signals.save(make_signal("S1", user_id="U1"))

    assert [
        x.entry_id for x in timeline.by_user("U1")
    ] == ["E1", "S1"]


def test_by_system(timeline, stores):
    events, signals, situations = stores

    events.save(make_event("E1", system_id="SYS-1"))
    events.save(make_event("E2", system_id="SYS-2"))
    situations.save(make_situation("SIT-1", system_id="SYS-1"))

    assert [
        x.entry_id for x in timeline.by_system("SYS-1")
    ] == ["E1", "SIT-1"]


def test_between_is_inclusive(timeline, stores):
    events, signals, situations = stores
    base = datetime(2026, 1, 1, 9, 0)

    events.save(make_event("E1", base))
    signals.save(make_signal("S1", base + timedelta(minutes=5)))
    situations.save(make_situation("SIT-1", base + timedelta(minutes=10)))

    result = timeline.between(
        base + timedelta(minutes=5),
        base + timedelta(minutes=10),
    )

    assert [x.entry_id for x in result] == ["S1", "SIT-1"]


def test_between_validates_range(timeline):
    start = datetime(2026, 1, 2)
    end = datetime(2026, 1, 1)

    with pytest.raises(ValueError):
        timeline.between(start, end)


def test_between_validates_types(timeline):
    with pytest.raises(TypeError):
        timeline.between("bad", datetime(2026, 1, 1))

    with pytest.raises(TypeError):
        timeline.between(datetime(2026, 1, 1), "bad")


def test_dimension_filters_validate_empty_values(timeline):
    with pytest.raises(ValueError):
        timeline.by_organization("")

    with pytest.raises(ValueError):
        timeline.by_user("")

    with pytest.raises(ValueError):
        timeline.by_system("")


def test_related_to_event(stores, timeline):
    events, signals, situations = stores

    events.save(make_event("E1"))
    signals.save(make_signal("S1", evidence=("E1",)))
    situations.save(make_situation("SIT-1", signal_ids=("S1",), evidence=("E1",)))

    result = timeline.related_to_event("E1")

    assert [x.entry_id for x in result] == ["E1", "S1", "SIT-1"]


def test_related_to_event_unknown(timeline):
    assert timeline.related_to_event("missing") == []


def test_related_to_signal(stores, timeline):
    events, signals, situations = stores

    signals.save(make_signal("S1"))
    situations.save(make_situation("SIT-1", signal_ids=("S1",)))

    result = timeline.related_to_signal("S1")

    assert [x.entry_id for x in result] == ["S1", "SIT-1"]


def test_related_to_signal_unknown(timeline):
    assert timeline.related_to_signal("missing") == []


def test_related_to_situation(stores, timeline):
    events, signals, situations = stores

    events.save(make_event("E1"))
    signals.save(make_signal("S1"))
    situations.save(make_situation("SIT-1"))

    result = timeline.related_to_situation("SIT-1")

    assert [x.entry_id for x in result] == ["E1", "S1", "SIT-1"]


def test_related_to_situation_unknown(timeline):
    assert timeline.related_to_situation("missing") == []


def test_timeline_survives_reinitialization(tmp_path):
    db = tmp_path / "restart.db"

    events = OperationalEventPersistence(db)
    signals = OperationalSignalPersistence(db)
    situations = OperationalSituationPersistence(db)

    events.save(make_event())
    signals.save(make_signal())
    situations.save(make_situation())

    timeline = OperationalTimeline(
        OperationalEventPersistence(db),
        OperationalSignalPersistence(db),
        OperationalSituationPersistence(db),
    )

    assert [x.entry_id for x in timeline.load_all()] == [
        "E1",
        "S1",
        "SIT-1",
    ]
