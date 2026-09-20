from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_intelligence import (
    BackgroundIntelligenceState,
)
from yoma.office.intelligence.background_pattern import (
    PatternType,
)
from yoma.office.intelligence.background_priority import (
    BackgroundPriorityAssessment,
    PriorityLevel,
    RiskLevel,
)
from yoma.office.intelligence.background_recommendation import (
    BackgroundRecommendation,
    BackgroundRecommendationResult,
    BackgroundRecommendationRuntime,
    RecommendationType,
)


BASE_TIME = datetime(
    2026, 9, 6, 12, 0, tzinfo=timezone.utc
)


def assessment(
    context_key="jira:ticket.updated",
    pattern_type=PatternType.REPEATED_EVENT,
    risk=RiskLevel.LOW,
    priority=PriorityLevel.LOW,
    occurrence_count=3,
    event_ids=("evt-1", "evt-2", "evt-3"),
):
    return BackgroundPriorityAssessment(
        context_key=context_key,
        pattern_type=pattern_type,
        risk_level=risk,
        priority=priority,
        occurrence_count=occurrence_count,
        event_ids=event_ids,
        reason="background risk assessment",
        assessed_at=BASE_TIME,
    )


def test_initial_state_is_stopped():
    runtime = BackgroundRecommendationRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop():
    runtime = BackgroundRecommendationRuntime()

    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False


def test_recommendation_requires_running_runtime():
    runtime = BackgroundRecommendationRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.recommend(
            [assessment()],
            created_at=BASE_TIME,
        )


def test_low_risk_creates_review_recommendation():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundRecommendationResult)
    assert result.processed_assessments == 1
    assert result.recommendations_created == 1

    recommendation = result.recommendations[0]

    assert isinstance(
        recommendation,
        BackgroundRecommendation,
    )
    assert (
        recommendation.recommendation_type
        == RecommendationType.REVIEW
    )
    assert recommendation.priority == PriorityLevel.LOW
    assert recommendation.risk_level == RiskLevel.LOW


def test_high_risk_creates_investigation_recommendation():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                risk=RiskLevel.HIGH,
                priority=PriorityLevel.HIGH,
            )
        ],
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert (
        recommendation.recommendation_type
        == RecommendationType.INVESTIGATE
    )
    assert recommendation.risk_level == RiskLevel.HIGH


def test_critical_high_priority_creates_investigation():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                risk=RiskLevel.CRITICAL,
                priority=PriorityLevel.HIGH,
            )
        ],
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert (
        recommendation.recommendation_type
        == RecommendationType.INVESTIGATE
    )
    assert recommendation.risk_level == RiskLevel.CRITICAL


def test_urgent_priority_creates_human_escalation():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                risk=RiskLevel.CRITICAL,
                priority=PriorityLevel.URGENT,
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
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert (
        recommendation.recommendation_type
        == RecommendationType.ESCALATE_TO_HUMAN
    )
    assert recommendation.priority == PriorityLevel.URGENT


def test_escalation_pattern_has_specific_title():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                pattern_type=PatternType.ESCALATION,
                risk=RiskLevel.MEDIUM,
                priority=PriorityLevel.NORMAL,
            )
        ],
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert "escalation" in (
        recommendation.title.lower()
    )


def test_recommendation_contains_next_step():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert recommendation.recommended_next_step
    assert len(
        recommendation.recommended_next_step
    ) > 10


def test_recommendation_reason_is_preserved():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    assert (
        result.recommendations[0].reason
        == "background risk assessment"
    )


def test_duplicate_assessment_is_not_recommended_twice():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    first = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    second = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    assert first.recommendations_created == 1
    assert second.recommendations_created == 0
    assert second.recommendations == ()


def test_recommendations_are_deterministically_ordered():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                context_key="zeta:ticket.updated",
                event_ids=("z-1", "z-2", "z-3"),
            ),
            assessment(
                context_key="alpha:ticket.updated",
                event_ids=("a-1", "a-2", "a-3"),
            ),
        ],
        created_at=BASE_TIME,
    )

    assert [
        item.context_key
        for item in result.recommendations
    ] == [
        "alpha:ticket.updated",
        "zeta:ticket.updated",
    ]


def test_timezone_is_required():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.recommend(
            [assessment()],
            created_at=datetime(
                2026, 9, 6, 12, 0
            ),
        )


def test_invalid_assessment_type_is_rejected():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.recommend(
            ["invalid"],
            created_at=BASE_TIME,
        )


def test_invalid_context_key_is_rejected():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    invalid = BackgroundPriorityAssessment(
        context_key="",
        pattern_type=PatternType.REPEATED_EVENT,
        risk_level=RiskLevel.LOW,
        priority=PriorityLevel.LOW,
        occurrence_count=3,
        event_ids=("evt-1", "evt-2", "evt-3"),
        reason="reason",
        assessed_at=BASE_TIME,
    )

    with pytest.raises(ValueError, match="context_key"):
        runtime.recommend(
            [invalid],
            created_at=BASE_TIME,
        )


def test_invalid_occurrence_count_is_rejected():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    invalid = BackgroundPriorityAssessment(
        context_key="jira:ticket.updated",
        pattern_type=PatternType.REPEATED_EVENT,
        risk_level=RiskLevel.LOW,
        priority=PriorityLevel.LOW,
        occurrence_count=0,
        event_ids=("evt-1",),
        reason="reason",
        assessed_at=BASE_TIME,
    )

    with pytest.raises(ValueError, match="occurrence_count"):
        runtime.recommend(
            [invalid],
            created_at=BASE_TIME,
        )


def test_governance_metadata_is_preserved():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert recommendation.metadata["source"] == "M37.7"
    assert recommendation.metadata["human_attention"] is True
    assert recommendation.metadata["recommendation_only"] is True
    assert recommendation.metadata["read_only"] is True
    assert recommendation.metadata["executable"] is False
    assert (
        recommendation.metadata[
            "requires_human_approval"
        ]
        is True
    )


def test_recommendation_is_never_executable():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                risk=RiskLevel.CRITICAL,
                priority=PriorityLevel.URGENT,
            )
        ],
        created_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert result.read_only is True
    assert result.executable is False
    assert result.requires_human_approval is True
    assert recommendation.executable is False
    assert recommendation.requires_human_approval is True


def test_event_ids_are_preserved():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    ids = ("evt-a", "evt-b", "evt-c")

    result = runtime.recommend(
        [
            assessment(
                event_ids=ids,
                occurrence_count=3,
            )
        ],
        created_at=BASE_TIME,
    )

    assert result.recommendations[0].event_ids == ids


def test_reset_allows_recommendation_again():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    first = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    assert first.recommendations_created == 1
    assert second.recommendations_created == 1


def test_recommendation_created_at_is_preserved():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [assessment()],
        created_at=BASE_TIME,
    )

    assert (
        result.recommendations[0].created_at
        == BASE_TIME
    )


def test_human_escalation_next_step_explicitly_requires_human():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [
            assessment(
                risk=RiskLevel.CRITICAL,
                priority=PriorityLevel.URGENT,
            )
        ],
        created_at=BASE_TIME,
    )

    next_step = (
        result.recommendations[0]
        .recommended_next_step
        .lower()
    )

    assert "human" in next_step
    assert "authorized" in next_step


def test_empty_input_is_safe():
    runtime = BackgroundRecommendationRuntime()
    runtime.start()

    result = runtime.recommend(
        [],
        created_at=BASE_TIME,
    )

    assert result.processed_assessments == 0
    assert result.recommendations_created == 0
    assert result.recommendations == ()
