from datetime import datetime, timedelta, timezone

from yoma.office.operations.situation import OperationalSituation
from yoma.office.operational_situation_persistence import (
    OperationalSituationPersistence,
)
from yoma.office.historical_pattern import (
    HistoricalPattern,
    HistoricalPatternDetector,
)


def make_situation(
    situation_id: str,
    detected_at: datetime,
    *,
    situation_type: str = "workload_pressure",
    organization_id: str = "org-1",
    user_id: str = "user-1",
    system_id: str | None = None,
    signal_ids: tuple[str, ...] = ("sig-1",),
    evidence_event_ids: tuple[str, ...] = ("evt-1",),
) -> OperationalSituation:
    return OperationalSituation(
        situation_id=situation_id,
        situation_type=situation_type,
        detected_at=detected_at,
        organization_id=organization_id,
        user_id=user_id,
        system_id=system_id,
        severity="warning",
        score=0.8,
        signal_ids=signal_ids,
        evidence_event_ids=evidence_event_ids,
        data={"source": "test"},
    )


def test_detects_repeated_situation_type(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation("sit-1", base)
    )
    store.save(
        make_situation(
            "sit-2",
            base + timedelta(hours=2),
        )
    )

    detector = HistoricalPatternDetector(store)

    patterns = detector.detect()

    assert len(patterns) == 1

    pattern = patterns[0]

    assert isinstance(pattern, HistoricalPattern)
    assert pattern.pattern_type == "historical_recurrence"
    assert pattern.situation_type == "workload_pressure"
    assert pattern.occurrence_count == 2
    assert pattern.recurring is True


def test_calculates_recurrence_interval(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(make_situation("sit-1", base))
    store.save(
        make_situation(
            "sit-2",
            base + timedelta(hours=2),
        )
    )
    store.save(
        make_situation(
            "sit-3",
            base + timedelta(hours=5),
        )
    )

    pattern = HistoricalPatternDetector(store).detect()[0]

    assert pattern.recurrence_intervals_seconds == (
        7200.0,
        10800.0,
    )

    assert pattern.average_recurrence_interval_seconds == 9000.0


def test_preserves_first_and_last_occurrence(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    first = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    last = datetime(2026, 1, 3, 15, 30, tzinfo=timezone.utc)

    store.save(make_situation("sit-1", first))
    store.save(make_situation("sit-2", last))

    pattern = HistoricalPatternDetector(store).detect()[0]

    assert pattern.first_occurred_at == first
    assert pattern.last_occurred_at == last


def test_does_not_create_pattern_for_single_occurrence(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    store.save(
        make_situation(
            "sit-1",
            datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
    )

    assert HistoricalPatternDetector(store).detect() == []


def test_groups_by_explicit_organization_and_user_scope(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation(
            "sit-a1",
            base,
            organization_id="org-a",
            user_id="user-a",
        )
    )
    store.save(
        make_situation(
            "sit-a2",
            base + timedelta(hours=1),
            organization_id="org-a",
            user_id="user-a",
        )
    )

    store.save(
        make_situation(
            "sit-b1",
            base,
            organization_id="org-a",
            user_id="user-b",
        )
    )
    store.save(
        make_situation(
            "sit-b2",
            base + timedelta(hours=1),
            organization_id="org-a",
            user_id="user-b",
        )
    )

    patterns = HistoricalPatternDetector(store).detect()

    assert len(patterns) == 2

    assert {
        pattern.user_id
        for pattern in patterns
    } == {"user-a", "user-b"}


def test_groups_by_system_when_present(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation(
            "sit-1",
            base,
            user_id=None,
            system_id="system-a",
        )
    )
    store.save(
        make_situation(
            "sit-2",
            base + timedelta(hours=1),
            user_id=None,
            system_id="system-a",
        )
    )

    pattern = HistoricalPatternDetector(store).detect()[0]

    assert pattern.system_id == "system-a"
    assert pattern.user_id is None


def test_preserves_repeated_signal_combinations(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation(
            "sit-1",
            base,
            signal_ids=("sig-b", "sig-a"),
        )
    )
    store.save(
        make_situation(
            "sit-2",
            base + timedelta(hours=1),
            signal_ids=("sig-a", "sig-b"),
        )
    )
    store.save(
        make_situation(
            "sit-3",
            base + timedelta(hours=2),
            signal_ids=("sig-c",),
        )
    )

    pattern = HistoricalPatternDetector(store).detect()[0]

    assert pattern.signal_combinations == (
        ("sig-a", "sig-b"),
        ("sig-c",),
    )


def test_situation_ids_are_chronological_and_deterministic(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation(
            "sit-later",
            base + timedelta(hours=2),
        )
    )
    store.save(
        make_situation(
            "sit-earlier",
            base,
        )
    )

    pattern = HistoricalPatternDetector(store).detect()[0]

    assert pattern.situation_ids == (
        "sit-earlier",
        "sit-later",
    )

    assert pattern.pattern_id.startswith(
        "HPAT-workload_pressure-org-1-user-1-GLOBAL-"
    )


def test_filter_by_type(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation(
            "work-1",
            base,
            situation_type="workload_pressure",
        )
    )
    store.save(
        make_situation(
            "work-2",
            base + timedelta(hours=1),
            situation_type="workload_pressure",
        )
    )
    store.save(
        make_situation(
            "meet-1",
            base,
            situation_type="meeting_pressure",
        )
    )
    store.save(
        make_situation(
            "meet-2",
            base + timedelta(hours=1),
            situation_type="meeting_pressure",
        )
    )

    detector = HistoricalPatternDetector(store)

    patterns = detector.detect_by_type("meeting_pressure")

    assert len(patterns) == 1
    assert patterns[0].situation_type == "meeting_pressure"


def test_filter_by_organization_and_user(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    store.save(
        make_situation(
            "a-1",
            base,
            organization_id="org-a",
            user_id="user-a",
        )
    )
    store.save(
        make_situation(
            "a-2",
            base + timedelta(hours=1),
            organization_id="org-a",
            user_id="user-a",
        )
    )

    store.save(
        make_situation(
            "b-1",
            base,
            organization_id="org-b",
            user_id="user-b",
        )
    )
    store.save(
        make_situation(
            "b-2",
            base + timedelta(hours=1),
            organization_id="org-b",
            user_id="user-b",
        )
    )

    detector = HistoricalPatternDetector(store)

    assert len(detector.detect_by_organization("org-a")) == 1
    assert len(detector.detect_by_user("user-b")) == 1


def test_validation_rejects_invalid_persistence():
    try:
        HistoricalPatternDetector(object())
        assert False
    except TypeError as exc:
        assert "OperationalSituationPersistence" in str(exc)


def test_validation_rejects_invalid_situation():
    class FakePersistence:
        def load_all(self):
            return [object()]

    try:
        HistoricalPatternDetector(FakePersistence()).detect()
        assert False
    except TypeError as exc:
        assert "OperationalSituation" in str(exc)


def test_custom_situations_can_be_analyzed_without_persistence(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    situations = [
        make_situation("sit-2", base + timedelta(hours=2)),
        make_situation("sit-1", base),
    ]

    patterns = HistoricalPatternDetector(store).detect(
        situations
    )

    assert len(patterns) == 1
    assert patterns[0].situation_ids == (
        "sit-1",
        "sit-2",
    )
