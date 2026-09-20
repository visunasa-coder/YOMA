from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_intelligence import (
    BackgroundEvent,
    BackgroundIntelligenceState,
)
from yoma.office.intelligence.background_intelligence_runtime import (
    BackgroundIntelligenceRuntimeResult,
    UnifiedBackgroundIntelligenceRuntime,
)
from yoma.office.intelligence.background_recommendation import (
    RecommendationType,
)


BASE_TIME = datetime(
    2026, 9, 6, 12, 0, tzinfo=timezone.utc
)


def event(
    event_id="evt-1",
    event_type="ticket.updated",
    source_system="jira",
    hour=12,
):
    return BackgroundEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=datetime(
            2026, 9, 6, hour, 0,
            tzinfo=timezone.utc,
        ),
        source_system=source_system,
        entity_id="ticket-1",
    )


def test_initial_state_is_stopped():
    runtime = UnifiedBackgroundIntelligenceRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_starts_all_pipeline_components():
    runtime = UnifiedBackgroundIntelligenceRuntime()

    runtime.start()

    assert runtime.running is True
    assert runtime.monitor.running is True
    assert runtime.trigger.running is True
    assert runtime.condition.running is True
    assert runtime.context.running is True
    assert runtime.pattern.running is True
    assert runtime.priority.running is True
    assert runtime.recommendation.running is True


def test_stop_stops_all_pipeline_components():
    runtime = UnifiedBackgroundIntelligenceRuntime()

    runtime.start()
    runtime.stop()

    assert runtime.running is False
    assert runtime.monitor.running is False
    assert runtime.trigger.running is False
    assert runtime.condition.running is False
    assert runtime.context.running is False
    assert runtime.pattern.running is False
    assert runtime.priority.running is False
    assert runtime.recommendation.running is False


def test_process_requires_running_runtime():
    runtime = UnifiedBackgroundIntelligenceRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.process(
            [event()],
            occurred_at=BASE_TIME,
        )


def test_complete_pipeline_produces_result():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        repetition_threshold=2,
        escalation_threshold=2,
    )
    runtime.start()

    result = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    assert isinstance(
        result,
        BackgroundIntelligenceRuntimeResult,
    )

    assert result.processed_events == 2
    assert result.detected_events == 2
    assert result.eligible_events == 2
    assert result.detected_conditions == 2
    assert result.accumulated_observations == 2
    assert result.detected_patterns == 1
    assert result.assessed_patterns == 1
    assert result.recommendations_created == 1


def test_complete_pipeline_produces_human_recommendation():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        repetition_threshold=2
    )
    runtime.start()

    result = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert recommendation.recommendation_type == (
        RecommendationType.REVIEW
    )
    assert recommendation.requires_human_approval is True
    assert recommendation.executable is False


def test_critical_pipeline_produces_investigation():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        critical_threshold=2
    )
    runtime.start()

    result = runtime.process(
        [
            event(
                "evt-1",
                event_type="service.outage",
            ),
            event(
                "evt-2",
                event_type="service.outage",
            ),
        ],
        occurred_at=BASE_TIME,
    )

    assert result.detected_patterns == 1
    assert result.assessed_patterns == 1
    assert result.recommendations_created == 1

    recommendation = result.recommendations[0]

    assert recommendation.risk_level.value == "critical"
    assert recommendation.recommendation_type == (
        RecommendationType.INVESTIGATE
    )


def test_event_filter_is_applied():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        event_types={"ticket.updated"}
    )
    runtime.start()

    result = runtime.process(
        [
            event(
                "evt-1",
                event_type="ticket.updated",
            ),
            event(
                "evt-2",
                event_type="ticket.closed",
            ),
        ],
        occurred_at=BASE_TIME,
    )

    assert result.eligible_events == 1
    assert result.detected_conditions == 1


def test_source_system_filter_is_applied():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        source_systems={"jira"}
    )
    runtime.start()

    result = runtime.process(
        [
            event(
                "evt-1",
                source_system="jira",
            ),
            event(
                "evt-2",
                source_system="salesforce",
            ),
        ],
        occurred_at=BASE_TIME,
    )

    assert result.eligible_events == 1


def test_duplicate_events_are_safely_ignored():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        repetition_threshold=2
    )
    runtime.start()

    first = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    second = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    assert first.processed_events == 2
    assert second.processed_events == 0
    assert second.recommendations_created == 0


def test_runtime_results_are_non_executable():
    runtime = UnifiedBackgroundIntelligenceRuntime()
    runtime.start()

    result = runtime.process(
        [event()],
        occurred_at=BASE_TIME,
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.requires_human_approval is True
    assert runtime.executable is False


def test_pipeline_metadata_identifies_m37_8():
    runtime = UnifiedBackgroundIntelligenceRuntime()
    runtime.start()

    result = runtime.process(
        [event()],
        occurred_at=BASE_TIME,
    )

    assert result.metadata["source"] == "M37.8"
    assert result.metadata["background_intelligence"] is True
    assert result.metadata["read_only"] is True
    assert result.metadata["executable"] is False
    assert (
        result.metadata["requires_human_approval"]
        is True
    )


def test_timezone_is_required():
    runtime = UnifiedBackgroundIntelligenceRuntime()
    runtime.start()

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.process(
            [event()],
            occurred_at=datetime(
                2026, 9, 6, 12, 0
            ),
        )


def test_empty_input_is_safe():
    runtime = UnifiedBackgroundIntelligenceRuntime()
    runtime.start()

    result = runtime.process(
        [],
        occurred_at=BASE_TIME,
    )

    assert result.processed_events == 0
    assert result.detected_events == 0
    assert result.eligible_events == 0
    assert result.detected_conditions == 0
    assert result.accumulated_observations == 0
    assert result.detected_patterns == 0
    assert result.assessed_patterns == 0
    assert result.recommendations_created == 0
    assert result.recommendations == ()


def test_reset_clears_entire_pipeline_state():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        repetition_threshold=2
    )
    runtime.start()

    first = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    assert first.recommendations_created == 1
    assert second.recommendations_created == 1


def test_lifecycle_is_idempotent():
    runtime = UnifiedBackgroundIntelligenceRuntime()

    runtime.start()
    runtime.start()

    assert runtime.running is True

    runtime.stop()
    runtime.stop()

    assert runtime.running is False


def test_component_configuration_is_forwarded():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        event_types={"custom.event"},
        source_systems={"custom"},
        max_observations_per_context=7,
        repetition_threshold=4,
        escalation_threshold=3,
        critical_threshold=3,
        high_occurrence_threshold=6,
        urgent_occurrence_threshold=7,
    )

    assert runtime.monitor._event_types == frozenset(
        {"custom.event"}
    )
    assert runtime.trigger._event_types == frozenset(
        {"custom.event"}
    )
    assert runtime.trigger._source_systems == frozenset(
        {"custom"}
    )
    assert runtime.context.max_observations_per_context == 7


def test_recommendation_never_becomes_authorization():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        repetition_threshold=2
    )
    runtime.start()

    result = runtime.process(
        [
            event("evt-1"),
            event("evt-2"),
        ],
        occurred_at=BASE_TIME,
    )

    recommendation = result.recommendations[0]

    assert recommendation.executable is False
    assert recommendation.requires_human_approval is True
    assert result.executable is False


def test_pipeline_preserves_event_order_deterministically():
    runtime = UnifiedBackgroundIntelligenceRuntime(
        repetition_threshold=2
    )
    runtime.start()

    result = runtime.process(
        [
            event("evt-2", hour=13),
            event("evt-1", hour=12),
        ],
        occurred_at=BASE_TIME,
    )

    assert result.processed_events == 2
    assert result.accumulated_observations == 2


def test_stop_prevents_processing_after_shutdown():
    runtime = UnifiedBackgroundIntelligenceRuntime()
    runtime.start()
    runtime.stop()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.process(
            [event()],
            occurred_at=BASE_TIME,
        )
