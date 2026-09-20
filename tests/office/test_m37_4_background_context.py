from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_condition import (
    BackgroundCondition,
    ConditionSeverity,
)
from yoma.office.intelligence.background_context import (
    BackgroundContextResult,
    BackgroundContextRuntime,
    ContextObservation,
)
from yoma.office.intelligence.background_intelligence import (
    BackgroundIntelligenceState,
)


BASE_TIME = datetime(
    2026, 9, 6, 12, 0, tzinfo=timezone.utc
)


def condition(
    event_id="evt-1",
    event_type="ticket.updated",
    source_system="jira",
    severity=ConditionSeverity.INFO,
    detected_at=BASE_TIME,
):
    return BackgroundCondition(
        event_id=event_id,
        event_type=event_type,
        source_system=source_system,
        condition="operational_event_detected",
        severity=severity,
        reason="background condition",
        detected_at=detected_at,
    )


def test_initial_state_is_stopped():
    runtime = BackgroundContextRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop():
    runtime = BackgroundContextRuntime()

    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False


def test_invalid_capacity_is_rejected():
    with pytest.raises(ValueError, match=">= 1"):
        BackgroundContextRuntime(
            max_observations_per_context=0
        )


def test_accumulation_requires_running_runtime():
    runtime = BackgroundContextRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.accumulate(
            [condition()],
            observed_at=BASE_TIME,
        )


def test_condition_is_accumulated():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundContextResult)
    assert result.processed_conditions == 1
    assert result.accumulated_observations == 1
    assert len(result.contexts) == 1

    snapshot = result.contexts[0]

    assert snapshot.context_key == "jira:ticket.updated"
    assert snapshot.observation_count == 1
    assert isinstance(
        snapshot.observations[0],
        ContextObservation,
    )


def test_multiple_conditions_accumulate_into_same_context():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [
            condition("evt-1"),
            condition("evt-2"),
            condition("evt-3"),
        ],
        observed_at=BASE_TIME,
    )

    assert result.processed_conditions == 3
    assert result.accumulated_observations == 3
    assert result.contexts[0].observation_count == 3


def test_context_is_bounded():
    runtime = BackgroundContextRuntime(
        max_observations_per_context=2
    )
    runtime.start()

    result = runtime.accumulate(
        [
            condition(
                "evt-1",
                detected_at=datetime(
                    2026, 9, 6, 10, 0,
                    tzinfo=timezone.utc,
                ),
            ),
            condition(
                "evt-2",
                detected_at=datetime(
                    2026, 9, 6, 11, 0,
                    tzinfo=timezone.utc,
                ),
            ),
            condition(
                "evt-3",
                detected_at=datetime(
                    2026, 9, 6, 12, 0,
                    tzinfo=timezone.utc,
                ),
            ),
        ],
        observed_at=BASE_TIME,
    )

    snapshot = result.contexts[0]

    assert snapshot.observation_count == 2
    assert [
        item.event_id
        for item in snapshot.observations
    ] == ["evt-2", "evt-3"]


def test_duplicate_condition_is_not_accumulated_twice():
    runtime = BackgroundContextRuntime()
    runtime.start()

    first = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    second = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    assert first.accumulated_observations == 1
    assert second.processed_conditions == 0
    assert second.accumulated_observations == 0
    assert second.contexts[0].observation_count == 1


def test_context_order_is_deterministic():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [
            condition("evt-2"),
            condition("evt-1"),
        ],
        observed_at=BASE_TIME,
    )

    assert [
        item.event_id
        for item in result.contexts[0].observations
    ] == ["evt-1", "evt-2"]


def test_contexts_are_sorted_by_key():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [
            condition(
                "evt-1",
                source_system="zeta",
            ),
            condition(
                "evt-2",
                source_system="alpha",
            ),
        ],
        observed_at=BASE_TIME,
    )

    assert [
        snapshot.context_key
        for snapshot in result.contexts
    ] == [
        "alpha:ticket.updated",
        "zeta:ticket.updated",
    ]


def test_timezone_is_required():
    runtime = BackgroundContextRuntime()
    runtime.start()

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.accumulate(
            [condition()],
            observed_at=datetime(2026, 9, 6, 12, 0),
        )


def test_invalid_condition_type_is_rejected():
    runtime = BackgroundContextRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.accumulate(
            ["invalid"],
            observed_at=BASE_TIME,
        )


def test_governance_metadata_is_preserved():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    snapshot = result.contexts[0]
    observation = snapshot.observations[0]

    assert observation.metadata["source"] == "M37.4"
    assert observation.metadata["read_only"] is True
    assert observation.metadata["executable"] is False
    assert (
        observation.metadata["requires_human_approval"]
        is True
    )


def test_result_is_non_executable():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.requires_human_approval is True


def test_latest_observation_is_exposed():
    runtime = BackgroundContextRuntime()
    runtime.start()

    later = datetime(
        2026, 9, 6, 13, 0,
        tzinfo=timezone.utc,
    )

    runtime.accumulate(
        [condition("evt-1")],
        observed_at=BASE_TIME,
    )

    result = runtime.accumulate(
        [condition("evt-2")],
        observed_at=later,
    )

    assert result.contexts[0].latest_observed_at == later


def test_reset_clears_context_and_allows_reprocessing():
    runtime = BackgroundContextRuntime()
    runtime.start()

    first = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.accumulate(
        [condition()],
        observed_at=BASE_TIME,
    )

    assert first.accumulated_observations == 1
    assert second.accumulated_observations == 1


def test_context_observation_preserves_condition_data():
    runtime = BackgroundContextRuntime()
    runtime.start()

    result = runtime.accumulate(
        [
            condition(
                event_id="evt-critical",
                event_type="service.outage",
                source_system="monitoring",
                severity=ConditionSeverity.CRITICAL,
            )
        ],
        observed_at=BASE_TIME,
    )

    observation = result.contexts[0].observations[0]

    assert observation.event_id == "evt-critical"
    assert observation.event_type == "service.outage"
    assert observation.source_system == "monitoring"
    assert observation.severity == ConditionSeverity.CRITICAL
