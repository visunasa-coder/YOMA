from datetime import datetime, timezone

import pytest

from yoma.office.operational_situation_persistence import (
    OperationalSituationPersistence,
)
from yoma.office.operations import OperationalSituation


def make_situation(
    situation_id: str = "sit-1",
    *,
    detected_at: datetime | None = None,
    organization_id: str | None = "org-1",
    user_id: str | None = "user-1",
    system_id: str | None = "system-1",
    situation_type: str = "workload_pressure",
    score: float = 0.85,
    severity: str = "warning",
    signal_ids: tuple[str, ...] = ("sig-1", "sig-2"),
    evidence_event_ids: tuple[str, ...] = (
        "evt-1",
        "evt-2",
        "evt-3",
    ),
) -> OperationalSituation:
    return OperationalSituation(
        situation_id=situation_id,
        situation_type=situation_type,
        detected_at=detected_at
        or datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc),
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        severity=severity,
        score=score,
        signal_ids=signal_ids,
        evidence_event_ids=evidence_event_ids,
        data={
            "signal_count": len(signal_ids),
            "source": "test",
        },
    )


def test_initializes_database(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    assert persistence.count() == 0


def test_save_and_get_round_trip(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )
    situation = make_situation()

    assert persistence.save(situation) is True
    assert persistence.get("sit-1") == situation


def test_signal_ids_are_preserved(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )
    situation = make_situation(
        signal_ids=("sig-a", "sig-b", "sig-c"),
    )

    persistence.save(situation)

    restored = persistence.get(situation.situation_id)

    assert restored is not None
    assert restored.signal_ids == ("sig-a", "sig-b", "sig-c")


def test_evidence_event_ids_are_preserved(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )
    situation = make_situation(
        evidence_event_ids=("evt-a", "evt-b"),
    )

    persistence.save(situation)

    restored = persistence.get(situation.situation_id)

    assert restored is not None
    assert restored.evidence_event_ids == ("evt-a", "evt-b")


def test_data_is_preserved(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )
    situation = make_situation()

    persistence.save(situation)

    restored = persistence.get(situation.situation_id)

    assert restored is not None
    assert restored.data == situation.data


def test_duplicate_situation_id_is_ignored(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )
    situation = make_situation()

    assert persistence.save(situation) is True
    assert persistence.save(situation) is False
    assert persistence.count() == 1


def test_save_many_returns_inserted_count(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    situations = [
        make_situation("sit-1"),
        make_situation("sit-2"),
        make_situation("sit-3"),
    ]

    assert persistence.save_many(situations) == 3
    assert persistence.save_many(situations) == 0
    assert persistence.count() == 3


def test_load_all_is_chronological_and_deterministic(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    later = make_situation(
        "sit-b",
        detected_at=datetime(
            2026, 9, 5, 12, 0, tzinfo=timezone.utc
        ),
    )
    earlier = make_situation(
        "sit-a",
        detected_at=datetime(
            2026, 9, 5, 10, 0, tzinfo=timezone.utc
        ),
    )

    persistence.save_many([later, earlier])

    assert persistence.load_all() == [earlier, later]


def test_filter_by_type(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    persistence.save(
        make_situation(
            "sit-1",
            situation_type="workload_pressure",
        )
    )
    persistence.save(
        make_situation(
            "sit-2",
            situation_type="other_condition",
        )
    )

    result = persistence.by_type("workload_pressure")

    assert [s.situation_id for s in result] == ["sit-1"]


def test_filter_by_organization_user_and_system(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    persistence.save(
        make_situation(
            "sit-org",
            organization_id="org-a",
            user_id="user-a",
            system_id="system-a",
        )
    )
    persistence.save(
        make_situation(
            "sit-other",
            organization_id="org-b",
            user_id="user-b",
            system_id="system-b",
        )
    )

    assert [
        s.situation_id
        for s in persistence.by_organization("org-a")
    ] == ["sit-org"]

    assert [
        s.situation_id
        for s in persistence.by_user("user-a")
    ] == ["sit-org"]

    assert [
        s.situation_id
        for s in persistence.by_system("system-a")
    ] == ["sit-org"]


def test_by_signal(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    persistence.save(
        make_situation(
            "sit-a",
            signal_ids=("sig-1", "sig-2"),
        )
    )
    persistence.save(
        make_situation(
            "sit-b",
            signal_ids=("sig-3",),
        )
    )

    result = persistence.by_signal("sig-2")

    assert [s.situation_id for s in result] == ["sit-a"]


def test_by_evidence_event(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    persistence.save(
        make_situation(
            "sit-a",
            evidence_event_ids=("evt-1", "evt-2"),
        )
    )
    persistence.save(
        make_situation(
            "sit-b",
            evidence_event_ids=("evt-3",),
        )
    )

    result = persistence.by_evidence_event("evt-2")

    assert [s.situation_id for s in result] == ["sit-a"]


def test_between_is_inclusive(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    start = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)
    middle = datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)

    persistence.save(
        make_situation("sit-start", detected_at=start)
    )
    persistence.save(
        make_situation("sit-middle", detected_at=middle)
    )
    persistence.save(
        make_situation("sit-end", detected_at=end)
    )

    result = persistence.between(start, end)

    assert [s.situation_id for s in result] == [
        "sit-start",
        "sit-middle",
        "sit-end",
    ]


def test_clear_removes_history(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    persistence.save(make_situation())

    persistence.clear()

    assert persistence.count() == 0
    assert persistence.get("sit-1") is None


def test_invalid_situation_is_rejected(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    with pytest.raises(TypeError, match="OperationalSituation"):
        persistence.save("not-a-situation")  # type: ignore[arg-type]


def test_invalid_filters_are_rejected(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    with pytest.raises(ValueError, match="situation_type"):
        persistence.by_type("")

    with pytest.raises(ValueError, match="organization_id"):
        persistence.by_organization("")

    with pytest.raises(ValueError, match="user_id"):
        persistence.by_user("")

    with pytest.raises(ValueError, match="system_id"):
        persistence.by_system("")


def test_invalid_signal_and_event_filters_are_rejected(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    with pytest.raises(ValueError, match="signal_id"):
        persistence.by_signal("")

    with pytest.raises(ValueError, match="event_id"):
        persistence.by_evidence_event("")


def test_invalid_time_range_is_rejected(tmp_path):
    persistence = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    start = datetime(
        2026, 9, 5, 12, 0, tzinfo=timezone.utc
    )
    end = datetime(
        2026, 9, 5, 10, 0, tzinfo=timezone.utc
    )

    with pytest.raises(ValueError, match="start"):
        persistence.between(start, end)


def test_restart_recovers_persisted_situations(tmp_path):
    db_path = tmp_path / "situations.db"

    first = OperationalSituationPersistence(db_path)
    situation = make_situation()
    first.save(situation)

    second = OperationalSituationPersistence(db_path)

    assert second.count() == 1
    assert second.get(situation.situation_id) == situation
