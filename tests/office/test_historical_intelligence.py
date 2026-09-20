from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.operations.model import (
    OperationalEvent,
    OperationalSignal,
)
from yoma.office.operations.situation import OperationalSituation

from yoma.office.operational_event_persistence import OperationalEventPersistence
from yoma.office.operational_signal_persistence import OperationalSignalPersistence
from yoma.office.operational_situation_persistence import OperationalSituationPersistence
from yoma.office.historical_intelligence import (
    HistoricalIntelligenceResult,
    HistoricalIntelligenceRuntime,
)


def make_event(event_id, timestamp):
    return OperationalEvent(
        event_id=event_id,
        event_type="workload.detected",
        occurred_at=timestamp,
        organization_id="org-1",
        user_id="user-1",
        system_id="system-1",
        source="test",
        location_id=None,
        severity="warning",
        data={"score": 0.9},
    )


def make_signal(signal_id, timestamp, event_id):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type="workload.high",
        detected_at=timestamp,
        organization_id="org-1",
        user_id="user-1",
        system_id="system-1",
        score=0.9,
        severity="warning",
        evidence_event_ids=(event_id,),
        data={"score": 0.9},
    )


def make_situation(situation_id, timestamp, signal_id, event_id):
    return OperationalSituation(
        situation_id=situation_id,
        situation_type="workload_pressure",
        detected_at=timestamp,
        organization_id="org-1",
        user_id="user-1",
        system_id="system-1",
        severity="warning",
        score=0.9,
        signal_ids=(signal_id,),
        evidence_event_ids=(event_id,),
        data={"source": "test"},
    )


def build_runtime(tmp_path):
    event_store = OperationalEventPersistence(
        tmp_path / "events.db"
    )
    signal_store = OperationalSignalPersistence(
        tmp_path / "signals.db"
    )
    situation_store = OperationalSituationPersistence(
        tmp_path / "situations.db"
    )

    return (
        HistoricalIntelligenceRuntime(
            event_store,
            signal_store,
            situation_store,
            window_days=7,
        ),
        event_store,
        signal_store,
        situation_store,
    )


def test_full_historical_pipeline(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    for index in range(4):
        timestamp = base + timedelta(days=index * 3)

        event_id = f"evt-{index}"
        signal_id = f"sig-{index}"
        situation_id = f"sit-{index}"

        events.save(
            make_event(event_id, timestamp)
        )

        signals.save(
            make_signal(
                signal_id,
                timestamp,
                event_id,
            )
        )

        situations.save(
            make_situation(
                situation_id,
                timestamp,
                signal_id,
                event_id,
            )
        )

    result = runtime.analyze()

    assert isinstance(
        result,
        HistoricalIntelligenceResult,
    )

    assert len(result.timeline) == 12
    assert len(result.patterns) == 1
    assert len(result.trends) == 1
    assert len(result.decision_contexts) == 4


def test_timeline_contains_all_historical_artifacts(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    timestamp = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    events.save(
        make_event("evt-1", timestamp)
    )
    signals.save(
        make_signal("sig-1", timestamp, "evt-1")
    )
    situations.save(
        make_situation(
            "sit-1",
            timestamp,
            "sig-1",
            "evt-1",
        )
    )

    result = runtime.analyze()

    assert {
        entry.entry_type
        for entry in result.timeline
    } == {
        "event",
        "signal",
        "situation",
    }


def test_detects_historical_recurrence(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    for index in range(3):
        timestamp = base + timedelta(days=index * 2)

        events.save(
            make_event(
                f"evt-{index}",
                timestamp,
            )
        )
        signals.save(
            make_signal(
                f"sig-{index}",
                timestamp,
                f"evt-{index}",
            )
        )
        situations.save(
            make_situation(
                f"sit-{index}",
                timestamp,
                f"sig-{index}",
                f"evt-{index}",
            )
        )

    result = runtime.analyze()

    assert len(result.patterns) == 1
    assert result.patterns[0].occurrence_count == 3
    assert result.patterns[0].recurring is True


def test_detects_trend_intelligence(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    # Historical occurrence.
    events.save(
        make_event("old-event", base)
    )
    signals.save(
        make_signal(
            "old-signal",
            base,
            "old-event",
        )
    )
    situations.save(
        make_situation(
            "old-situation",
            base,
            "old-signal",
            "old-event",
        )
    )

    # Four recent occurrences.
    recent = base + timedelta(days=10)

    for index in range(4):
        timestamp = recent + timedelta(days=index)

        events.save(
            make_event(
                f"recent-event-{index}",
                timestamp,
            )
        )
        signals.save(
            make_signal(
                f"recent-signal-{index}",
                timestamp,
                f"recent-event-{index}",
            )
        )
        situations.save(
            make_situation(
                f"recent-situation-{index}",
                timestamp,
                f"recent-signal-{index}",
                f"recent-event-{index}",
            )
        )

    result = runtime.analyze()

    assert len(result.trends) == 1
    assert result.trends[0].trend_direction == "increasing"


def test_decision_context_contains_historical_evidence(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    for index in range(2):
        timestamp = base + timedelta(days=index)

        events.save(
            make_event(
                f"evt-{index}",
                timestamp,
            )
        )
        signals.save(
            make_signal(
                f"sig-{index}",
                timestamp,
                f"evt-{index}",
            )
        )
        situations.save(
            make_situation(
                f"sit-{index}",
                timestamp,
                f"sig-{index}",
                f"evt-{index}",
            )
        )

    result = runtime.analyze()

    context = result.decision_contexts[-1]

    assert context.historical_context_available is True
    assert context.recurring is True
    assert context.historical_pattern_id is not None
    assert context.requires_human_approval is True


def test_context_for_current_situation(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    base = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    events.save(make_event("evt-1", base))
    signals.save(make_signal("sig-1", base, "evt-1"))
    situations.save(
        make_situation(
            "sit-1",
            base,
            "sig-1",
            "evt-1",
        )
    )

    current = make_situation(
        "current",
        base + timedelta(days=2),
        "sig-current",
        "evt-current",
    )

    context = runtime.context_for(current)

    assert context.situation_id == "current"
    assert context.historical_context_available is True
    assert context.requires_human_approval is True


def test_scope_is_preserved(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    timestamp = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    events.save(
        make_event("evt-1", timestamp)
    )
    signals.save(
        make_signal("sig-1", timestamp, "evt-1")
    )
    situations.save(
        make_situation(
            "sit-1",
            timestamp,
            "sig-1",
            "evt-1",
        )
    )

    result = runtime.analyze()

    context = result.decision_contexts[0]

    assert context.organization_id == "org-1"
    assert context.user_id == "user-1"
    assert context.system_id == "system-1"


def test_restart_reconstructs_historical_intelligence(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    timestamp = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    events.save(make_event("evt-1", timestamp))
    signals.save(make_signal("sig-1", timestamp, "evt-1"))
    situations.save(
        make_situation(
            "sit-1",
            timestamp,
            "sig-1",
            "evt-1",
        )
    )

    # Re-open the stores through a new runtime.
    runtime2 = HistoricalIntelligenceRuntime(
        OperationalEventPersistence(tmp_path / "events.db"),
        OperationalSignalPersistence(tmp_path / "signals.db"),
        OperationalSituationPersistence(tmp_path / "situations.db"),
    )

    result = runtime2.analyze()

    assert len(result.timeline) == 3
    assert len(result.decision_contexts) == 1


def test_clear_removes_all_historical_artifacts(tmp_path):
    runtime, events, signals, situations = build_runtime(tmp_path)

    timestamp = datetime(
        2026, 1, 1, 10, 0,
        tzinfo=timezone.utc,
    )

    events.save(make_event("evt-1", timestamp))
    signals.save(make_signal("sig-1", timestamp, "evt-1"))
    situations.save(
        make_situation(
            "sit-1",
            timestamp,
            "sig-1",
            "evt-1",
        )
    )

    assert len(runtime.analyze().timeline) == 3

    runtime.clear()

    result = runtime.analyze()

    assert result.timeline == ()
    assert result.patterns == ()
    assert result.trends == ()
    assert result.decision_contexts == ()


def test_no_history_is_safe(tmp_path):
    runtime, _, _, _ = build_runtime(tmp_path)

    result = runtime.analyze()

    assert result.timeline == ()
    assert result.patterns == ()
    assert result.trends == ()
    assert result.decision_contexts == ()


def test_invalid_store_rejected():
    with pytest.raises(TypeError):
        HistoricalIntelligenceRuntime(
            object(),
            object(),
            object(),
        )


def test_invalid_context_situation_rejected(tmp_path):
    runtime, _, _, _ = build_runtime(tmp_path)

    with pytest.raises(TypeError):
        runtime.context_for(object())
