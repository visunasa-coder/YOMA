from datetime import datetime, timezone

import pytest

from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.operations import OperationalEvent


def event(
    event_id: str,
    event_type: str,
    user_id: str | None = "U001",
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


def test_engine_registers_rule():
    engine = OperationalIntelligenceEngine()

    engine.register_rule("workload", high_workload_rule)

    assert engine.list_rules() == ["workload"]


def test_duplicate_rule_rejected():
    engine = OperationalIntelligenceEngine()

    engine.register_rule("workload", high_workload_rule)

    with pytest.raises(ValueError):
        engine.register_rule("workload", high_workload_rule)


def test_engine_analyzes_events():
    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    signals = engine.analyze([
        event(
            "EV001",
            "workload.high",
            data={"score": 0.9},
        )
    ])

    assert len(signals) == 1
    assert signals[0].signal_type == "workload.high"
    assert signals[0].score == 0.9
    assert signals[0].user_id == "U001"


def test_irrelevant_events_produce_no_signal():
    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    signals = engine.analyze([
        event("EV001", "attendance.check_in"),
        event("EV002", "calendar.event"),
    ])

    assert signals == []


def test_group_by_user():
    engine = OperationalIntelligenceEngine()

    events = [
        event("EV001", "attendance.check_in", "U001"),
        event("EV002", "calendar.event", "U001"),
        event("EV003", "attendance.check_in", "U002"),
    ]

    grouped = engine.group_by_user(events)

    assert set(grouped) == {"U001", "U002"}
    assert len(grouped["U001"]) == 2
    assert len(grouped["U002"]) == 1


def test_group_by_system():
    engine = OperationalIntelligenceEngine()

    events = [
        event("EV001", "hardware.online", None),
        OperationalEvent(
            event_id="EV002",
            event_type="hardware.online",
            occurred_at=datetime.now(timezone.utc),
            system_id="SYS001",
            source="hardware",
        ),
    ]

    grouped = engine.group_by_system(events)

    assert set(grouped) == {"SYS001"}
    assert len(grouped["SYS001"]) == 1


def test_unregister_rule():
    engine = OperationalIntelligenceEngine()

    engine.register_rule("workload", high_workload_rule)

    assert engine.unregister_rule("workload") is True
    assert engine.unregister_rule("workload") is False
    assert engine.list_rules() == []


def test_invalid_rule_output_is_rejected():
    engine = OperationalIntelligenceEngine()

    def bad_rule(events):
        return ["not a signal"]

    engine.register_rule("bad", bad_rule)

    with pytest.raises(TypeError):
        engine.analyze([])


def test_high_workload_rule_preserves_evidence():
    signals = high_workload_rule([
        event(
            "EV123",
            "workload.high",
            data={"score": 0.8},
        )
    ])

    assert signals[0].evidence_event_ids == ("EV123",)
