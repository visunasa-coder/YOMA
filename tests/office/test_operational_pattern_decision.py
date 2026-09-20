from datetime import datetime, timezone

import pytest

from yoma.office.decision import (
    OperationalPatternDecisionAdapter,
)
from yoma.office.operations import (
    OperationalPattern,
    OperationalSignal,
)


def make_signal(
    signal_id: str,
    signal_type: str = "workload.high",
) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        detected_at=datetime(
            2026, 9, 5, 10, 0, tzinfo=timezone.utc
        ),
        organization_id="ORG001",
        user_id="EMP001",
        score=0.8,
        severity="warning",
        evidence_event_ids=(f"EV-{signal_id}",),
    )


def make_pattern() -> OperationalPattern:
    return OperationalPattern(
        pattern_id="PAT-TEAM-TEAM001-SIT001-SIT002",
        pattern_type="cross_situation",
        detected_at=datetime(
            2026, 9, 5, 10, 0, tzinfo=timezone.utc
        ),
        correlation_dimension="team",
        correlation_id="TEAM001",
        situation_ids=("SIT001", "SIT002"),
        signal_ids=("SIG001", "SIG002"),
        evidence_event_ids=("EV-SIG001", "EV-SIG002"),
        severity="critical",
        score=0.9,
    )


def test_adapts_pattern_to_decision_context():
    adapter = OperationalPatternDecisionAdapter()

    pattern = make_pattern()
    signals = [
        make_signal("SIG001"),
        make_signal("SIG002", "meeting_load.high"),
    ]

    context = adapter.adapt(pattern, signals)

    assert context.signal.signal_id == "SIG001"
    assert len(context.recommendations) == 1
    assert context.recommendations[0]["type"] == (
        "operational_pattern_review"
    )


def test_preserves_pattern_metadata():
    adapter = OperationalPatternDecisionAdapter()

    context = adapter.adapt(
        make_pattern(),
        [
            make_signal("SIG001"),
            make_signal("SIG002"),
        ],
    )

    recommendation = context.recommendations[0]

    assert recommendation["pattern_id"] == (
        "PAT-TEAM-TEAM001-SIT001-SIT002"
    )
    assert recommendation["correlation_dimension"] == "team"
    assert recommendation["correlation_id"] == "TEAM001"
    assert recommendation["situation_ids"] == (
        "SIT001",
        "SIT002",
    )


def test_pattern_decision_requires_human_approval():
    adapter = OperationalPatternDecisionAdapter()

    context = adapter.adapt(
        make_pattern(),
        [
            make_signal("SIG001"),
            make_signal("SIG002"),
        ],
    )

    assert context.requires_human_approval is True
    assert context.actions == ()


def test_missing_source_signal_is_rejected():
    adapter = OperationalPatternDecisionAdapter()

    with pytest.raises(ValueError):
        adapter.adapt(
            make_pattern(),
            [make_signal("SIG001")],
        )


def test_duplicate_source_signal_is_rejected():
    adapter = OperationalPatternDecisionAdapter()

    with pytest.raises(ValueError):
        adapter.adapt(
            make_pattern(),
            [
                make_signal("SIG001"),
                make_signal("SIG001"),
            ],
        )


def test_invalid_pattern_is_rejected():
    adapter = OperationalPatternDecisionAdapter()

    with pytest.raises(TypeError):
        adapter.adapt(
            "not-a-pattern",
            [make_signal("SIG001")],
        )


def test_invalid_signal_is_rejected():
    adapter = OperationalPatternDecisionAdapter()

    with pytest.raises(TypeError):
        adapter.adapt(
            make_pattern(),
            ["not-a-signal"],
        )


def test_empty_pattern_signals_are_rejected():
    adapter = OperationalPatternDecisionAdapter()

    pattern = OperationalPattern(
        pattern_id="PAT001",
        pattern_type="cross_situation",
        detected_at=datetime.now(timezone.utc),
        correlation_dimension="team",
        correlation_id="TEAM001",
    )

    with pytest.raises(ValueError):
        adapter.adapt(
            pattern,
            [make_signal("SIG001")],
        )
