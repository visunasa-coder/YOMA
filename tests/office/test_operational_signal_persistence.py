from datetime import datetime, timezone

import pytest

from yoma.office.operational_signal_persistence import (
    OperationalSignalPersistence,
)
from yoma.office.operations import OperationalSignal


def make_signal(
    signal_id: str = "sig-1",
    *,
    detected_at: datetime | None = None,
    organization_id: str | None = "org-1",
    user_id: str | None = "user-1",
    system_id: str | None = "system-1",
    signal_type: str = "workload.high",
    score: float = 0.9,
    severity: str = "warning",
    evidence_event_ids: tuple[str, ...] = ("evt-1", "evt-2"),
) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        detected_at=detected_at
        or datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        score=score,
        severity=severity,
        evidence_event_ids=evidence_event_ids,
        data={"rule": "high_workload", "score": score},
    )


def test_initializes_database(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    assert persistence.count() == 0


def test_save_and_get_round_trip(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")
    signal = make_signal()

    assert persistence.save(signal) is True
    assert persistence.get("sig-1") == signal


def test_evidence_event_ids_are_preserved(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")
    signal = make_signal(
        evidence_event_ids=("evt-a", "evt-b", "evt-c"),
    )

    persistence.save(signal)

    restored = persistence.get(signal.signal_id)

    assert restored is not None
    assert restored.evidence_event_ids == ("evt-a", "evt-b", "evt-c")


def test_duplicate_signal_id_is_ignored(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")
    signal = make_signal()

    assert persistence.save(signal) is True
    assert persistence.save(signal) is False
    assert persistence.count() == 1


def test_save_many_returns_inserted_count(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    signals = [
        make_signal("sig-1"),
        make_signal("sig-2"),
        make_signal("sig-3"),
    ]

    assert persistence.save_many(signals) == 3
    assert persistence.save_many(signals) == 0
    assert persistence.count() == 3


def test_load_all_is_chronological_and_deterministic(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    later = make_signal(
        "sig-b",
        detected_at=datetime(
            2026, 9, 5, 12, 0, tzinfo=timezone.utc
        ),
    )
    earlier = make_signal(
        "sig-a",
        detected_at=datetime(
            2026, 9, 5, 10, 0, tzinfo=timezone.utc
        ),
    )

    persistence.save_many([later, earlier])

    assert persistence.load_all() == [earlier, later]


def test_filter_by_type(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    persistence.save(make_signal("sig-1", signal_type="workload.high"))
    persistence.save(make_signal("sig-2", signal_type="meeting_load.high"))

    result = persistence.by_type("workload.high")

    assert [signal.signal_id for signal in result] == ["sig-1"]


def test_filter_by_organization_user_and_system(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    persistence.save(
        make_signal(
            "sig-org",
            organization_id="org-a",
            user_id="user-a",
            system_id="system-a",
        )
    )
    persistence.save(
        make_signal(
            "sig-other",
            organization_id="org-b",
            user_id="user-b",
            system_id="system-b",
        )
    )

    assert [
        signal.signal_id
        for signal in persistence.by_organization("org-a")
    ] == ["sig-org"]

    assert [
        signal.signal_id
        for signal in persistence.by_user("user-a")
    ] == ["sig-org"]

    assert [
        signal.signal_id
        for signal in persistence.by_system("system-a")
    ] == ["sig-org"]


def test_between_is_inclusive(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    start = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)
    middle = datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)

    persistence.save(make_signal("sig-start", detected_at=start))
    persistence.save(make_signal("sig-middle", detected_at=middle))
    persistence.save(make_signal("sig-end", detected_at=end))

    result = persistence.between(start, end)

    assert [signal.signal_id for signal in result] == [
        "sig-start",
        "sig-middle",
        "sig-end",
    ]


def test_by_evidence_event(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    persistence.save(
        make_signal(
            "sig-a",
            evidence_event_ids=("evt-1", "evt-2"),
        )
    )
    persistence.save(
        make_signal(
            "sig-b",
            evidence_event_ids=("evt-3",),
        )
    )

    result = persistence.by_evidence_event("evt-2")

    assert [signal.signal_id for signal in result] == ["sig-a"]


def test_clear_removes_history(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    persistence.save(make_signal())

    persistence.clear()

    assert persistence.count() == 0
    assert persistence.get("sig-1") is None


def test_invalid_signal_is_rejected(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    with pytest.raises(TypeError, match="OperationalSignal"):
        persistence.save("not-a-signal")  # type: ignore[arg-type]


def test_invalid_filters_are_rejected(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    with pytest.raises(ValueError, match="signal_type"):
        persistence.by_type("")

    with pytest.raises(ValueError, match="organization_id"):
        persistence.by_organization("")

    with pytest.raises(ValueError, match="user_id"):
        persistence.by_user("")

    with pytest.raises(ValueError, match="system_id"):
        persistence.by_system("")


def test_invalid_time_range_is_rejected(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    start = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="start"):
        persistence.between(start, end)


def test_invalid_evidence_event_is_rejected(tmp_path):
    persistence = OperationalSignalPersistence(tmp_path / "signals.db")

    with pytest.raises(ValueError, match="event_id"):
        persistence.by_evidence_event("")


def test_restart_recovers_persisted_signals(tmp_path):
    db_path = tmp_path / "signals.db"

    first = OperationalSignalPersistence(db_path)
    signal = make_signal()
    first.save(signal)

    second = OperationalSignalPersistence(db_path)

    assert second.count() == 1
    assert second.get(signal.signal_id) == signal
