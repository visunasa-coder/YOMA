from datetime import datetime, timedelta, timezone

from yoma.office.operations.situation import OperationalSituation
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_decision_context import (
    HistoricalDecisionContext,
    HistoricalDecisionContextBuilder,
)


def make_situation(
    situation_id: str = "sit-current",
) -> OperationalSituation:
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=datetime(
            2026, 1, 10, 10, 0,
            tzinfo=timezone.utc,
        ),
        organization_id="org-1",
        user_id="user-1",
        system_id=None,
        severity="warning",
        score=0.9,
        signal_ids=("sig-1",),
        evidence_event_ids=("evt-1",),
        data={},
    )


def make_pattern() -> HistoricalPattern:
    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    return HistoricalPattern(
        pattern_id="HPAT-workload_pressure-org-1-user-1-GLOBAL-s1-s2",
        pattern_type="historical_recurrence",
        situation_type="workload_pressure",
        organization_id="org-1",
        user_id="user-1",
        system_id=None,
        occurrence_count=3,
        first_occurred_at=base,
        last_occurred_at=base + timedelta(days=9),
        recurrence_intervals_seconds=(
            86400.0,
            172800.0,
        ),
        signal_combinations=(
            ("sig-1",),
        ),
        situation_ids=(
            "s1",
            "s2",
            "s3",
        ),
    )


def make_trend() -> BaselineTrend:
    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    return BaselineTrend(
        situation_type="workload_pressure",
        organization_id="org-1",
        user_id="user-1",
        system_id=None,
        total_occurrences=3,
        historical_days=10.0,
        baseline_daily_frequency=0.3,
        recent_occurrences=3,
        previous_occurrences=1,
        window_days=7.0,
        recent_daily_frequency=3 / 7,
        previous_daily_frequency=1 / 7,
        frequency_change=2 / 7,
        deviation_from_baseline=0.4285714285714286,
        trend_ratio=3.0,
        trend_direction="increasing",
        first_occurred_at=base,
        last_occurred_at=base + timedelta(days=9),
        average_recurrence_interval_seconds=129600.0,
        situation_ids=("s1", "s2", "s3"),
    )


def test_builds_historical_context():
    builder = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    )

    context = builder.build(make_situation())

    assert isinstance(
        context,
        HistoricalDecisionContext,
    )

    assert context.situation_id == "sit-current"
    assert context.occurrence_count == 3
    assert (
        context.historical_pattern_id
        == "HPAT-workload_pressure-org-1-user-1-GLOBAL-s1-s2"
    )


def test_carries_baseline_and_trend():
    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(make_situation())

    assert context.baseline_daily_frequency == 0.3
    assert context.recent_daily_frequency == 3 / 7
    assert context.previous_daily_frequency == 1 / 7
    assert context.frequency_change == 2 / 7
    assert context.trend_ratio == 3.0
    assert context.trend_direction == "increasing"
    assert context.deviation_from_baseline > 0


def test_marks_recurring_and_above_baseline():
    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(make_situation())

    assert context.recurring is True
    assert context.above_baseline is True
    assert context.below_baseline is False
    assert context.historical_context_available is True


def test_preserves_historical_situation_ids():
    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(make_situation())

    assert context.historical_situation_ids == (
        "s1",
        "s2",
        "s3",
    )


def test_preserves_recurrence_interval():
    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(make_situation())

    assert (
        context.average_recurrence_interval_seconds
        == 129600.0
    )


def test_builds_evidence():
    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(make_situation())

    assert (
        "historical_pattern:HPAT-workload_pressure-org-1-user-1-GLOBAL-s1-s2"
        in context.evidence
    )
    assert "historical_occurrences:3" in context.evidence
    assert "trend_direction:increasing" in context.evidence


def test_no_match_is_safe():
    situation = make_situation()

    unrelated = OperationalSituation(
        situation_id="other",
        situation_type="meeting_pressure",
        detected_at=situation.detected_at,
        organization_id="org-2",
        user_id="user-2",
        system_id=None,
        severity="info",
        score=0.2,
        signal_ids=("sig-x",),
        evidence_event_ids=("evt-x",),
        data={},
    )

    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(unrelated)

    assert context.occurrence_count == 0
    assert context.historical_pattern_id is None
    assert context.trend_direction == "unknown"
    assert context.trend_ratio == 1.0
    assert context.historical_context_available is False
    assert (
        context.evidence
        == ("no_historical_match:other",)
    )


def test_scope_matching_is_explicit():
    pattern = make_pattern()

    wrong_scope = HistoricalPattern(
        pattern_id="wrong",
        pattern_type="historical_recurrence",
        situation_type="workload_pressure",
        organization_id="org-2",
        user_id="user-1",
        system_id=None,
        occurrence_count=99,
        first_occurred_at=pattern.first_occurred_at,
        last_occurred_at=pattern.last_occurred_at,
        recurrence_intervals_seconds=(),
        signal_combinations=(),
        situation_ids=("wrong",),
    )

    context = HistoricalDecisionContextBuilder(
        [wrong_scope, pattern],
        [make_trend()],
    ).build(make_situation())

    assert context.historical_pattern_id == pattern.pattern_id
    assert context.occurrence_count == 3


def test_prefers_highest_occurrence_pattern():
    pattern = make_pattern()

    stronger = HistoricalPattern(
        pattern_id="stronger",
        pattern_type="historical_recurrence",
        situation_type=pattern.situation_type,
        organization_id=pattern.organization_id,
        user_id=pattern.user_id,
        system_id=pattern.system_id,
        occurrence_count=8,
        first_occurred_at=pattern.first_occurred_at,
        last_occurred_at=pattern.last_occurred_at,
        recurrence_intervals_seconds=(),
        signal_combinations=(),
        situation_ids=("many",),
    )

    context = HistoricalDecisionContextBuilder(
        [pattern, stronger],
        [make_trend()],
    ).build(make_situation())

    assert context.historical_pattern_id == "stronger"
    assert context.occurrence_count == 8


def test_build_many():
    builder = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    )

    contexts = builder.build_many(
        [
            make_situation("s1"),
            make_situation("s2"),
        ]
    )

    assert len(contexts) == 2
    assert contexts[0].situation_id == "s1"
    assert contexts[1].situation_id == "s2"


def test_human_approval_is_always_required():
    context = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    ).build(make_situation())

    assert context.requires_human_approval is True


def test_invalid_pattern_rejected():
    try:
        HistoricalDecisionContextBuilder(
            [object()],
            [],
        )
        assert False
    except TypeError as exc:
        assert "HistoricalPattern" in str(exc)


def test_invalid_trend_rejected():
    try:
        HistoricalDecisionContextBuilder(
            [],
            [object()],
        )
        assert False
    except TypeError as exc:
        assert "BaselineTrend" in str(exc)


def test_invalid_situation_rejected():
    builder = HistoricalDecisionContextBuilder(
        [make_pattern()],
        [make_trend()],
    )

    try:
        builder.build(object())
        assert False
    except TypeError as exc:
        assert "OperationalSituation" in str(exc)
