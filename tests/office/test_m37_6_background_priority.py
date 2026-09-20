from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_condition import (
    ConditionSeverity,
)
from yoma.office.intelligence.background_intelligence import (
    BackgroundIntelligenceState,
)
from yoma.office.intelligence.background_pattern import (
    BackgroundPattern,
    PatternType,
)
from yoma.office.intelligence.background_priority import (
    BackgroundPriorityAssessment,
    BackgroundPriorityResult,
    BackgroundPriorityRuntime,
    PriorityLevel,
    RiskLevel,
)


BASE_TIME = datetime(
    2026, 9, 6, 12, 0, tzinfo=timezone.utc
)


def pattern(
    pattern_type=PatternType.REPEATED_EVENT,
    occurrence_count=3,
    context_key="jira:ticket.updated",
    event_ids=("evt-1", "evt-2", "evt-3"),
):
    return BackgroundPattern(
        context_key=context_key,
        pattern_type=pattern_type,
        severity=(
            ConditionSeverity.CRITICAL
            if pattern_type == PatternType.CRITICAL_REPETITION
            else (
                ConditionSeverity.WARNING
                if pattern_type == PatternType.ESCALATION
                else ConditionSeverity.INFO
            )
        ),
        occurrence_count=occurrence_count,
        event_ids=event_ids,
        reason="background pattern",
        detected_at=BASE_TIME,
    )


def test_initial_state_is_stopped():
    runtime = BackgroundPriorityRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop():
    runtime = BackgroundPriorityRuntime()

    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False


def test_invalid_thresholds_are_rejected():
    with pytest.raises(ValueError, match=">= 1"):
        BackgroundPriorityRuntime(
            high_occurrence_threshold=0
        )

    with pytest.raises(ValueError, match=">= 1"):
        BackgroundPriorityRuntime(
            urgent_occurrence_threshold=0
        )


def test_assessment_requires_running_runtime():
    runtime = BackgroundPriorityRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.assess(
            [pattern()],
            assessed_at=BASE_TIME,
        )


def test_low_repetition_is_low_risk_low_priority():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    result = runtime.assess(
        [pattern(occurrence_count=3)],
        assessed_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundPriorityResult)
    assert result.processed_patterns == 1
    assert result.assessed_patterns == 1

    assessment = result.assessments[0]

    assert isinstance(
        assessment,
        BackgroundPriorityAssessment,
    )
    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.priority == PriorityLevel.LOW


def test_high_repetition_becomes_medium_risk():
    runtime = BackgroundPriorityRuntime(
        high_occurrence_threshold=5
    )
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                occurrence_count=5,
                event_ids=(
                    "evt-1",
                    "evt-2",
                    "evt-3",
                    "evt-4",
                    "evt-5",
                ),
            )
        ],
        assessed_at=BASE_TIME,
    )

    assessment = result.assessments[0]

    assert assessment.risk_level == RiskLevel.MEDIUM
    assert assessment.priority == PriorityLevel.NORMAL


def test_escalation_pattern_is_medium_or_high_based_on_count():
    runtime = BackgroundPriorityRuntime(
        high_occurrence_threshold=5
    )
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                pattern_type=PatternType.ESCALATION,
                occurrence_count=2,
                event_ids=("evt-1", "evt-2"),
            )
        ],
        assessed_at=BASE_TIME,
    )

    assessment = result.assessments[0]

    assert assessment.risk_level == RiskLevel.MEDIUM
    assert assessment.priority == PriorityLevel.NORMAL


def test_repeated_escalation_becomes_high_risk():
    runtime = BackgroundPriorityRuntime(
        high_occurrence_threshold=5
    )
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                pattern_type=PatternType.ESCALATION,
                occurrence_count=5,
                event_ids=(
                    "evt-1",
                    "evt-2",
                    "evt-3",
                    "evt-4",
                    "evt-5",
                ),
            )
        ],
        assessed_at=BASE_TIME,
    )

    assessment = result.assessments[0]

    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.priority == PriorityLevel.HIGH


def test_critical_pattern_is_high_priority():
    runtime = BackgroundPriorityRuntime(
        urgent_occurrence_threshold=5
    )
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                pattern_type=PatternType.CRITICAL_REPETITION,
                occurrence_count=2,
                event_ids=("evt-1", "evt-2"),
            )
        ],
        assessed_at=BASE_TIME,
    )

    assessment = result.assessments[0]

    assert assessment.risk_level == RiskLevel.CRITICAL
    assert assessment.priority == PriorityLevel.HIGH


def test_repeated_critical_pattern_becomes_urgent():
    runtime = BackgroundPriorityRuntime(
        urgent_occurrence_threshold=5
    )
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                pattern_type=PatternType.CRITICAL_REPETITION,
                occurrence_count=5,
                event_ids=(
                    "evt-1",
                    "evt-2",
                    "evt-3",
                    "evt-4",
                    "evt-5",
                ),
            )
        ],
        assessed_at=BASE_TIME,
    )

    assessment = result.assessments[0]

    assert assessment.risk_level == RiskLevel.CRITICAL
    assert assessment.priority == PriorityLevel.URGENT


def test_duplicate_pattern_is_not_reassessed():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    first = runtime.assess(
        [pattern()],
        assessed_at=BASE_TIME,
    )

    second = runtime.assess(
        [pattern()],
        assessed_at=BASE_TIME,
    )

    assert first.assessed_patterns == 1
    assert second.assessed_patterns == 0
    assert second.assessments == ()


def test_assessments_are_deterministically_ordered():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                context_key="zeta:ticket.updated",
                event_ids=("z-1", "z-2", "z-3"),
            ),
            pattern(
                context_key="alpha:ticket.updated",
                event_ids=("a-1", "a-2", "a-3"),
            ),
        ],
        assessed_at=BASE_TIME,
    )

    assert [
        item.context_key
        for item in result.assessments
    ] == [
        "alpha:ticket.updated",
        "zeta:ticket.updated",
    ]


def test_timezone_is_required():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.assess(
            [pattern()],
            assessed_at=datetime(
                2026, 9, 6, 12, 0
            ),
        )


def test_invalid_pattern_type_is_rejected():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.assess(
            ["invalid"],
            assessed_at=BASE_TIME,
        )


def test_invalid_context_key_is_rejected():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    invalid = pattern()
    invalid = BackgroundPattern(
        context_key="",
        pattern_type=invalid.pattern_type,
        severity=invalid.severity,
        occurrence_count=invalid.occurrence_count,
        event_ids=invalid.event_ids,
        reason=invalid.reason,
        detected_at=invalid.detected_at,
    )

    with pytest.raises(ValueError, match="context_key"):
        runtime.assess(
            [invalid],
            assessed_at=BASE_TIME,
        )


def test_invalid_occurrence_count_is_rejected():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    invalid = pattern(occurrence_count=0)

    with pytest.raises(ValueError, match="occurrence_count"):
        runtime.assess(
            [invalid],
            assessed_at=BASE_TIME,
        )


def test_governance_metadata_is_preserved():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    result = runtime.assess(
        [pattern()],
        assessed_at=BASE_TIME,
    )

    assessment = result.assessments[0]

    assert assessment.metadata["source"] == "M37.6"
    assert assessment.metadata["read_only"] is True
    assert assessment.metadata["executable"] is False
    assert (
        assessment.metadata["requires_human_approval"]
        is True
    )


def test_result_is_non_executable():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    result = runtime.assess(
        [pattern()],
        assessed_at=BASE_TIME,
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.requires_human_approval is True


def test_event_ids_are_preserved():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    ids = ("evt-a", "evt-b", "evt-c")

    result = runtime.assess(
        [
            pattern(
                event_ids=ids,
                occurrence_count=3,
            )
        ],
        assessed_at=BASE_TIME,
    )

    assert result.assessments[0].event_ids == ids


def test_reset_allows_reassessment():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    first = runtime.assess(
        [pattern()],
        assessed_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.assess(
        [pattern()],
        assessed_at=BASE_TIME,
    )

    assert first.assessed_patterns == 1
    assert second.assessed_patterns == 1


def test_reason_is_explainable():
    runtime = BackgroundPriorityRuntime()
    runtime.start()

    result = runtime.assess(
        [
            pattern(
                pattern_type=PatternType.CRITICAL_REPETITION,
                occurrence_count=2,
                event_ids=("evt-1", "evt-2"),
            )
        ],
        assessed_at=BASE_TIME,
    )

    reason = result.assessments[0].reason

    assert "critical" in reason.lower()
    assert len(reason) > 10
