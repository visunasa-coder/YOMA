from datetime import datetime, timedelta, timezone

from yoma.office.operations.situation import OperationalSituation
from yoma.office.operational_situation_persistence import (
    OperationalSituationPersistence,
)
from yoma.office.baseline_trend import (
    BaselineTrend,
    BaselineTrendAnalyzer,
)


def make_situation(
    situation_id: str,
    detected_at: datetime,
    *,
    situation_type: str = "workload_pressure",
    organization_id: str = "org-1",
    user_id: str = "user-1",
    system_id: str | None = None,
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
        signal_ids=("sig-1",),
        evidence_event_ids=("evt-1",),
        data={"source": "test"},
    )


def test_empty_history_returns_no_results(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    assert BaselineTrendAnalyzer(store).analyze() == []


def test_creates_baseline_from_history(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(make_situation("s1", base))
    store.save(
        make_situation(
            "s2",
            base + timedelta(days=2),
        )
    )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert isinstance(result, BaselineTrend)
    assert result.total_occurrences == 2
    assert result.first_occurred_at == base
    assert result.last_occurred_at == base + timedelta(days=2)
    assert result.baseline_daily_frequency > 0


def test_detects_increasing_frequency(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "old-1",
            base,
        )
    )

    recent_base = base + timedelta(days=10)

    for index in range(4):
        store.save(
            make_situation(
                f"recent-{index}",
                recent_base + timedelta(days=index),
            )
        )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert result.recent_occurrences == 4
    assert result.trend_direction == "increasing"
    assert result.frequency_change > 0


def test_detects_decreasing_frequency(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    for index in range(4):
        store.save(
            make_situation(
                f"old-{index}",
                base + timedelta(days=index),
            )
        )

    recent = base + timedelta(days=10)

    store.save(
        make_situation(
            "recent",
            recent,
        )
    )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert result.previous_occurrences > result.recent_occurrences
    assert result.trend_direction == "decreasing"
    assert result.frequency_change < 0


def test_detects_stable_frequency(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "old-1",
            base,
        )
    )
    store.save(
        make_situation(
            "old-2",
            base + timedelta(days=1),
        )
    )

    recent = base + timedelta(days=10)

    store.save(
        make_situation(
            "recent-1",
            recent,
        )
    )
    store.save(
        make_situation(
            "recent-2",
            recent + timedelta(days=1),
        )
    )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert result.previous_occurrences == 2
    assert result.recent_occurrences == 2
    assert result.trend_direction == "stable"


def test_calculates_frequency_change(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "old",
            base,
        )
    )

    recent = base + timedelta(days=10)

    store.save(
        make_situation(
            "recent-1",
            recent,
        )
    )
    store.save(
        make_situation(
            "recent-2",
            recent + timedelta(days=1),
        )
    )
    store.save(
        make_situation(
            "recent-3",
            recent + timedelta(days=2),
        )
    )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert result.recent_daily_frequency == 3 / 7
    assert result.previous_daily_frequency == 1 / 7
    assert result.frequency_change == 2 / 7


def test_calculates_trend_ratio(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "old",
            base,
        )
    )

    recent = base + timedelta(days=10)

    store.save(
        make_situation(
            "recent-1",
            recent,
        )
    )
    store.save(
        make_situation(
            "recent-2",
            recent + timedelta(days=1),
        )
    )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert result.trend_ratio == 2.0


def test_calculates_baseline_deviation(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "old",
            base,
        )
    )

    recent = base + timedelta(days=10)

    store.save(
        make_situation(
            "recent-1",
            recent,
        )
    )
    store.save(
        make_situation(
            "recent-2",
            recent + timedelta(days=1),
        )
    )
    store.save(
        make_situation(
            "recent-3",
            recent + timedelta(days=2),
        )
    )

    result = BaselineTrendAnalyzer(
        store,
        window_days=7,
    ).analyze()[0]

    assert result.above_baseline is True
    assert result.deviation_from_baseline > 0


def test_calculates_recurrence_interval(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(make_situation("s1", base))
    store.save(
        make_situation(
            "s2",
            base + timedelta(hours=2),
        )
    )
    store.save(
        make_situation(
            "s3",
            base + timedelta(hours=5),
        )
    )

    result = BaselineTrendAnalyzer(store).analyze()[0]

    assert result.average_recurrence_interval_seconds == 9000.0


def test_groups_by_explicit_scope(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "a1",
            base,
            organization_id="org-a",
            user_id="user-a",
        )
    )
    store.save(
        make_situation(
            "a2",
            base + timedelta(days=1),
            organization_id="org-a",
            user_id="user-a",
        )
    )

    store.save(
        make_situation(
            "b1",
            base,
            organization_id="org-b",
            user_id="user-b",
        )
    )
    store.save(
        make_situation(
            "b2",
            base + timedelta(days=1),
            organization_id="org-b",
            user_id="user-b",
        )
    )

    results = BaselineTrendAnalyzer(store).analyze()

    assert len(results) == 2
    assert {
        result.organization_id
        for result in results
    } == {"org-a", "org-b"}


def test_filter_by_type(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "w1",
            base,
            situation_type="workload_pressure",
        )
    )
    store.save(
        make_situation(
            "w2",
            base + timedelta(days=1),
            situation_type="workload_pressure",
        )
    )

    store.save(
        make_situation(
            "m1",
            base,
            situation_type="meeting_pressure",
        )
    )
    store.save(
        make_situation(
            "m2",
            base + timedelta(days=1),
            situation_type="meeting_pressure",
        )
    )

    results = BaselineTrendAnalyzer(store).analyze_by_type(
        "meeting_pressure"
    )

    assert len(results) == 1
    assert results[0].situation_type == "meeting_pressure"


def test_filter_by_user_and_system(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    store.save(
        make_situation(
            "u1",
            base,
            user_id="user-a",
        )
    )
    store.save(
        make_situation(
            "u2",
            base + timedelta(days=1),
            user_id="user-a",
        )
    )

    store.save(
        make_situation(
            "sys1",
            base,
            user_id=None,
            system_id="system-a",
        )
    )
    store.save(
        make_situation(
            "sys2",
            base + timedelta(days=1),
            user_id=None,
            system_id="system-a",
        )
    )

    analyzer = BaselineTrendAnalyzer(store)

    assert len(
        analyzer.analyze_by_user("user-a")
    ) == 1

    assert len(
        analyzer.analyze_by_system("system-a")
    ) == 1


def test_validation():
    try:
        BaselineTrendAnalyzer(object())
        assert False
    except TypeError as exc:
        assert "OperationalSituationPersistence" in str(exc)

    class FakePersistence:
        def load_all(self):
            return []

    valid = BaselineTrendAnalyzer(FakePersistence()) if False else None
    assert valid is None


def test_rejects_invalid_configuration(tmp_path):
    store = OperationalSituationPersistence(
        db_path=tmp_path / "test.db"
    )

    try:
        BaselineTrendAnalyzer(
            store,
            window_days=0,
        )
        assert False
    except ValueError as exc:
        assert "window_days" in str(exc)

    try:
        BaselineTrendAnalyzer(
            store,
            stable_threshold=-1,
        )
        assert False
    except ValueError as exc:
        assert "stable_threshold" in str(exc)
