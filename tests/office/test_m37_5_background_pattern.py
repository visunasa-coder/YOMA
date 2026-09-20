from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_condition import (
    BackgroundCondition,
    ConditionSeverity,
)
from yoma.office.intelligence.background_context import (
    BackgroundContextRuntime,
)
from yoma.office.intelligence.background_pattern import (
    BackgroundPattern,
    BackgroundPatternResult,
    BackgroundPatternRuntime,
    PatternType,
)
from yoma.office.intelligence.background_intelligence import (
    BackgroundIntelligenceState,
)


BASE_TIME = datetime(
    2026, 9, 6, 12, 0, tzinfo=timezone.utc
)


def condition(
    event_id,
    severity=ConditionSeverity.INFO,
    condition_name="operational_event_detected",
    hour=12,
):
    return BackgroundCondition(
        event_id=event_id,
        event_type="ticket.updated",
        source_system="jira",
        condition=condition_name,
        severity=severity,
        reason="background condition",
        detected_at=datetime(
            2026, 9, 6, hour, 0,
            tzinfo=timezone.utc,
        ),
    )


def context(
    observations,
    key="jira:ticket.updated",
):
    runtime = BackgroundContextRuntime(
        max_observations_per_context=20
    )
    runtime.start()

    result = runtime.accumulate(
        observations,
        observed_at=BASE_TIME,
    )

    return result.contexts[0]


def test_initial_state_is_stopped():
    runtime = BackgroundPatternRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop():
    runtime = BackgroundPatternRuntime()

    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False


def test_invalid_thresholds_are_rejected():
    with pytest.raises(ValueError, match=">= 2"):
        BackgroundPatternRuntime(
            repetition_threshold=1
        )

    with pytest.raises(ValueError, match=">= 2"):
        BackgroundPatternRuntime(
            escalation_threshold=1
        )

    with pytest.raises(ValueError, match=">= 2"):
        BackgroundPatternRuntime(
            critical_threshold=1
        )


def test_recognition_requires_running_runtime():
    runtime = BackgroundPatternRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.recognize(
            [],
            detected_at=BASE_TIME,
        )


def test_repeated_event_pattern_is_detected():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=3
    )
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
            condition("evt-3"),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundPatternResult)
    assert result.processed_contexts == 1
    assert result.detected_patterns == 1

    pattern = result.patterns[0]

    assert isinstance(pattern, BackgroundPattern)
    assert pattern.pattern_type == PatternType.REPEATED_EVENT
    assert pattern.occurrence_count == 3
    assert pattern.severity == ConditionSeverity.INFO


def test_below_threshold_produces_no_pattern():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=3
    )
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert result.detected_patterns == 0
    assert result.patterns == ()


def test_warning_escalation_pattern_is_detected():
    runtime = BackgroundPatternRuntime(
        escalation_threshold=2
    )
    runtime.start()

    snapshot = context(
        [
            condition(
                "evt-1",
                condition_name="warning_operational_condition",
                severity=ConditionSeverity.WARNING,
            ),
            condition(
                "evt-2",
                condition_name="warning_operational_condition",
                severity=ConditionSeverity.WARNING,
            ),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    pattern = result.patterns[0]

    assert pattern.pattern_type == PatternType.ESCALATION
    assert pattern.occurrence_count == 2
    assert pattern.severity == ConditionSeverity.WARNING


def test_repeated_critical_conditions_take_priority():
    runtime = BackgroundPatternRuntime(
        critical_threshold=2,
        escalation_threshold=2,
    )
    runtime.start()

    snapshot = context(
        [
            condition(
                "evt-1",
                condition_name="critical_operational_condition",
                severity=ConditionSeverity.CRITICAL,
            ),
            condition(
                "evt-2",
                condition_name="critical_operational_condition",
                severity=ConditionSeverity.CRITICAL,
            ),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    pattern = result.patterns[0]

    assert pattern.pattern_type == PatternType.CRITICAL_REPETITION
    assert pattern.severity == ConditionSeverity.CRITICAL
    assert pattern.occurrence_count == 2


def test_duplicate_context_is_not_reprocessed():
    runtime = BackgroundPatternRuntime()
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
            condition("evt-3"),
        ]
    )

    first = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    second = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert first.detected_patterns == 1
    assert second.detected_patterns == 0


def test_patterns_are_deterministically_ordered():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=2
    )
    runtime.start()

    snapshot_a = context(
        [
            condition("a-1"),
            condition("a-2"),
        ]
    )

    snapshot_b = context(
        [
            condition("b-1"),
            condition("b-2"),
        ],
        key="salesforce:ticket.updated",
    )

    # Build a second snapshot with the requested stable key.
    from yoma.office.intelligence.background_context import (
        BackgroundContextSnapshot,
    )

    snapshot_b = BackgroundContextSnapshot(
        context_key="salesforce:ticket.updated",
        observations=snapshot_b.observations,
        observation_count=snapshot_b.observation_count,
        latest_observed_at=snapshot_b.latest_observed_at,
        metadata=snapshot_b.metadata,
    )

    result = runtime.recognize(
        [snapshot_b, snapshot_a],
        detected_at=BASE_TIME,
    )

    assert [
        pattern.context_key
        for pattern in result.patterns
    ] == [
        "jira:ticket.updated",
        "salesforce:ticket.updated",
    ]


def test_event_ids_are_preserved():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=2
    )
    runtime.start()

    snapshot = context(
        [
            condition("evt-a"),
            condition("evt-b"),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert result.patterns[0].event_ids == (
        "evt-a",
        "evt-b",
    )


def test_timezone_is_required():
    runtime = BackgroundPatternRuntime()
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
            condition("evt-3"),
        ]
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.recognize(
            [snapshot],
            detected_at=datetime(2026, 9, 6, 12, 0),
        )


def test_invalid_context_type_is_rejected():
    runtime = BackgroundPatternRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.recognize(
            ["invalid"],
            detected_at=BASE_TIME,
        )


def test_pattern_governance_metadata_is_preserved():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=2
    )
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    pattern = result.patterns[0]

    assert pattern.metadata["source"] == "M37.5"
    assert pattern.metadata["read_only"] is True
    assert pattern.metadata["executable"] is False
    assert (
        pattern.metadata["requires_human_approval"]
        is True
    )


def test_result_is_non_executable():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=2
    )
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
        ]
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.requires_human_approval is True


def test_reset_allows_context_to_be_processed_again():
    runtime = BackgroundPatternRuntime(
        repetition_threshold=2
    )
    runtime.start()

    snapshot = context(
        [
            condition("evt-1"),
            condition("evt-2"),
        ]
    )

    first = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert first.detected_patterns == 1
    assert second.detected_patterns == 1


def test_empty_context_does_not_create_pattern():
    runtime = BackgroundPatternRuntime()
    runtime.start()

    from yoma.office.intelligence.background_context import (
        BackgroundContextSnapshot,
    )

    snapshot = BackgroundContextSnapshot(
        context_key="empty",
        observations=(),
        observation_count=0,
        latest_observed_at=None,
    )

    result = runtime.recognize(
        [snapshot],
        detected_at=BASE_TIME,
    )

    assert result.processed_contexts == 1
    assert result.detected_patterns == 0
    assert result.patterns == ()
