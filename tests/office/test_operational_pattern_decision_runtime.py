from datetime import datetime, timezone

import pytest

from yoma.office.decision.pattern import (
    OperationalPatternDecisionAdapter,
)
from yoma.office.intelligence.operational_pattern_runtime import (
    OperationalPatternResult,
)
from yoma.office.intelligence.operational_pattern_decision_runtime import (
    OperationalPatternDecisionRuntime,
)
from yoma.office.operations import (
    OperationalPattern,
    OperationalSignal,
)


def signal(
    signal_id: str,
    signal_type: str = "workload.high",
    score: float = 0.8,
):
    return OperationalSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        detected_at=datetime.now(timezone.utc),
        user_id="U001",
        score=score,
        severity="high",
        evidence_event_ids=(f"EV-{signal_id}",),
    )


def pattern(
    pattern_id: str = "PAT-001",
    signal_ids: tuple[str, ...] = ("SIG001", "SIG002"),
):
    return OperationalPattern(
        pattern_id=pattern_id,
        pattern_type="cross_situation",
        detected_at=datetime.now(timezone.utc),
        correlation_dimension="team",
        correlation_id="TEAM001",
        situation_ids=("SIT001", "SIT002"),
        signal_ids=signal_ids,
        evidence_event_ids=("EV-SIT001", "EV-SIT002"),
        severity="high",
        score=0.85,
    )


def make_result(
    patterns,
):
    return OperationalPatternResult(
        contexts=(),
        patterns=tuple(patterns),
    )


def make_signals():
    return (
        signal("SIG001", score=0.8),
        signal("SIG002", score=0.9),
    )


def test_pattern_decision_runtime_adapts_pattern():
    runtime = OperationalPatternDecisionRuntime()

    result = runtime.process(
        make_result([pattern()]),
        make_signals(),
    )

    assert len(result.patterns) == 1
    assert len(result.decisions) == 1


def test_pattern_decision_runtime_preserves_pattern():
    runtime = OperationalPatternDecisionRuntime()

    source = pattern()

    result = runtime.process(
        make_result([source]),
        make_signals(),
    )

    assert result.patterns == (source,)


def test_pattern_decision_runtime_creates_advisory_decision():
    runtime = OperationalPatternDecisionRuntime()

    result = runtime.process(
        make_result([pattern()]),
        make_signals(),
    )

    decision = result.decisions[0]

    assert decision.requires_human_approval is True
    assert decision.actions == ()
    assert len(decision.recommendations) == 1


def test_pattern_decision_runtime_preserves_pattern_metadata():
    runtime = OperationalPatternDecisionRuntime()

    result = runtime.process(
        make_result([pattern()]),
        make_signals(),
    )

    recommendation = result.decisions[0].recommendations[0]

    assert recommendation["type"] == "operational_pattern_review"
    assert recommendation["pattern_id"] == "PAT-001"
    assert recommendation["correlation_dimension"] == "team"
    assert recommendation["correlation_id"] == "TEAM001"
    assert recommendation["situation_ids"] == (
        "SIT001",
        "SIT002",
    )


def test_pattern_decision_runtime_uses_deterministic_signal_anchor():
    runtime = OperationalPatternDecisionRuntime()

    result = runtime.process(
        make_result([
            pattern(
                signal_ids=("SIG002", "SIG001"),
            )
        ]),
        make_signals(),
    )

    decision = result.decisions[0]

    assert decision.signal.signal_id == "SIG001"


def test_pattern_decision_runtime_handles_multiple_patterns():
    runtime = OperationalPatternDecisionRuntime()

    patterns = [
        pattern("PAT-001"),
        pattern("PAT-002"),
    ]

    result = runtime.process(
        make_result(patterns),
        make_signals(),
    )

    assert len(result.decisions) == 2


def test_pattern_decision_runtime_handles_empty_patterns():
    runtime = OperationalPatternDecisionRuntime()

    result = runtime.process(
        make_result([]),
        make_signals(),
    )

    assert result.patterns == ()
    assert result.decisions == ()


def test_pattern_decision_runtime_rejects_invalid_result():
    runtime = OperationalPatternDecisionRuntime()

    with pytest.raises(TypeError):
        runtime.process(
            "invalid",
            make_signals(),
        )


def test_pattern_decision_runtime_tracks_last_result():
    runtime = OperationalPatternDecisionRuntime()

    result = runtime.process(
        make_result([pattern()]),
        make_signals(),
    )

    assert runtime.last_result is result
