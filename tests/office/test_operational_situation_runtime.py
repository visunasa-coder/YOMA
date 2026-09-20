from datetime import datetime, timezone

import pytest

from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.intelligence.operational_runtime import (
    OperationalIntelligenceRuntime,
)
from yoma.office.intelligence.operational_situation_runtime import (
    OperationalSituationRuntime,
)
from yoma.office.operations import (
    OperationalEvent,
    OperationalSignal,
)


def event(
    event_id: str,
    event_type: str,
    user_id: str = "U001",
    data: dict | None = None,
):
    return OperationalEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        user_id=user_id,
        source="test",
        data=data or {},
    )


def make_intelligence_runtime():
    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    return OperationalIntelligenceRuntime(
        intelligence_engine=engine,
    )


def signal(
    signal_id: str,
    signal_type: str,
    score: float,
    event_id: str,
    user_id: str = "U001",
):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        detected_at=datetime.now(timezone.utc),
        user_id=user_id,
        score=score,
        severity="high",
        evidence_event_ids=(event_id,),
    )


def test_situation_runtime_processes_intelligence_result():
    intelligence_runtime = make_intelligence_runtime()
    situation_runtime = OperationalSituationRuntime()

    intelligence_result = intelligence_runtime.process([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.9},
        )
    ])

    result = situation_runtime.process(intelligence_result)

    assert len(result.events) == 1
    assert len(result.signals) == 1
    assert len(result.situations) == 1


def test_situation_runtime_creates_workload_pressure_situation():
    intelligence_runtime = make_intelligence_runtime()
    situation_runtime = OperationalSituationRuntime()

    intelligence_result = intelligence_runtime.process([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.85},
        )
    ])

    result = situation_runtime.process(intelligence_result)

    situation = result.situations[0]

    assert situation.situation_type == "workload_pressure"
    assert situation.user_id == "U001"
    assert situation.score == 0.85


def test_situation_runtime_preserves_events_and_signals():
    intelligence_runtime = make_intelligence_runtime()
    situation_runtime = OperationalSituationRuntime()

    intelligence_result = intelligence_runtime.process([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.8},
        )
    ])

    result = situation_runtime.process(intelligence_result)

    assert result.events == intelligence_result.events
    assert result.signals == intelligence_result.signals


def test_situation_runtime_preserves_evidence():
    intelligence_runtime = make_intelligence_runtime()
    situation_runtime = OperationalSituationRuntime()

    intelligence_result = intelligence_runtime.process([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.8},
        )
    ])

    result = situation_runtime.process(intelligence_result)

    assert result.situations[0].evidence_event_ids == ("EV001",)


def test_situation_runtime_correlates_multiple_signals():
    situation_runtime = OperationalSituationRuntime()

    signals = [
        signal(
            "SIG001",
            "workload.high",
            0.8,
            "EV001",
        ),
        signal(
            "SIG002",
            "meeting_load.high",
            0.6,
            "EV002",
        ),
        signal(
            "SIG003",
            "deadline_pressure.high",
            0.9,
            "EV003",
        ),
    ]

    from yoma.office.intelligence.operational_runtime import (
        OperationalIntelligenceResult,
    )

    intelligence_result = OperationalIntelligenceResult(
        events=(
            event("EV001", "workload.high"),
            event("EV002", "meeting_load.high"),
            event("EV003", "deadline_pressure.high"),
        ),
        signals=tuple(signals),
    )

    result = situation_runtime.process(intelligence_result)

    assert len(result.situations) == 1
    assert len(result.situations[0].signal_ids) == 3
    assert result.situations[0].evidence_event_ids == (
        "EV001",
        "EV002",
        "EV003",
    )


def test_situation_runtime_separates_users():
    situation_runtime = OperationalSituationRuntime()

    signals = [
        signal(
            "SIG001",
            "workload.high",
            0.8,
            "EV001",
            "U001",
        ),
        signal(
            "SIG002",
            "workload.high",
            0.9,
            "EV002",
            "U002",
        ),
    ]

    from yoma.office.intelligence.operational_runtime import (
        OperationalIntelligenceResult,
    )

    intelligence_result = OperationalIntelligenceResult(
        events=(
            event("EV001", "workload.high", "U001"),
            event("EV002", "workload.high", "U002"),
        ),
        signals=tuple(signals),
    )

    result = situation_runtime.process(intelligence_result)

    assert len(result.situations) == 2
    assert {s.user_id for s in result.situations} == {
        "U001",
        "U002",
    }


def test_situation_runtime_handles_empty_intelligence_result():
    intelligence_runtime = make_intelligence_runtime()
    situation_runtime = OperationalSituationRuntime()

    intelligence_result = intelligence_runtime.process([])

    result = situation_runtime.process(intelligence_result)

    assert result.events == ()
    assert result.signals == ()
    assert result.situations == ()


def test_situation_runtime_rejects_invalid_input():
    situation_runtime = OperationalSituationRuntime()

    with pytest.raises(TypeError):
        situation_runtime.process("invalid")


def test_situation_runtime_tracks_last_result():
    intelligence_runtime = make_intelligence_runtime()
    situation_runtime = OperationalSituationRuntime()

    intelligence_result = intelligence_runtime.process([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.95},
        )
    ])

    result = situation_runtime.process(intelligence_result)

    assert situation_runtime.last_result is result
