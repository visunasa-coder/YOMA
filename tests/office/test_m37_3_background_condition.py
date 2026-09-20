from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_intelligence import (
    BackgroundIntelligenceState,
)
from yoma.office.intelligence.background_trigger import (
    BackgroundTriggerDecision,
    TriggerEligibility,
)
from yoma.office.intelligence.background_condition import (
    BackgroundCondition,
    BackgroundConditionResult,
    BackgroundConditionRuntime,
    ConditionSeverity,
)


BASE_TIME = datetime(
    2026, 9, 6, 12, 0, tzinfo=timezone.utc
)


def decision(
    event_id="evt-1",
    event_type="ticket.updated",
    source_system="jira",
    eligibility=TriggerEligibility.ELIGIBLE,
):
    return BackgroundTriggerDecision(
        event_id=event_id,
        event_type=event_type,
        source_system=source_system,
        eligibility=eligibility,
        reason="background_intelligence_trigger",
        evaluated_at=BASE_TIME,
    )


def test_initial_state_is_stopped():
    runtime = BackgroundConditionRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop():
    runtime = BackgroundConditionRuntime()

    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False


def test_detection_requires_running_runtime():
    runtime = BackgroundConditionRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.detect(
            [decision()],
            detected_at=BASE_TIME,
        )


def test_eligible_event_creates_condition():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundConditionResult)
    assert result.processed_events == 1
    assert result.detected_conditions == 1

    condition = result.conditions[0]

    assert isinstance(condition, BackgroundCondition)
    assert condition.event_id == "evt-1"
    assert condition.condition == "operational_event_detected"
    assert condition.severity == ConditionSeverity.INFO


def test_warning_event_is_classified_as_warning():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [decision(event_type="incident.created")],
        detected_at=BASE_TIME,
    )

    condition = result.conditions[0]

    assert condition.severity == ConditionSeverity.WARNING
    assert condition.condition == "warning_operational_condition"


def test_critical_event_is_classified_as_critical():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [decision(event_type="service.outage")],
        detected_at=BASE_TIME,
    )

    condition = result.conditions[0]

    assert condition.severity == ConditionSeverity.CRITICAL
    assert condition.condition == "critical_operational_condition"


def test_ineligible_event_does_not_create_condition():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [
            decision(
                eligibility=TriggerEligibility.INELIGIBLE
            )
        ],
        detected_at=BASE_TIME,
    )

    assert result.processed_events == 1
    assert result.detected_conditions == 0
    assert result.conditions == ()


def test_duplicate_event_is_not_reprocessed():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    first = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    second = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    assert first.detected_conditions == 1
    assert second.detected_conditions == 0
    assert second.conditions == ()


def test_results_are_deterministic():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [
            decision("evt-2"),
            decision("evt-1"),
        ],
        detected_at=BASE_TIME,
    )

    assert [
        item.event_id
        for item in result.conditions
    ] == [
        "evt-1",
        "evt-2",
    ]


def test_timezone_is_required():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.detect(
            [decision()],
            detected_at=datetime(2026, 9, 6, 12, 0),
        )


def test_invalid_decision_type_is_rejected():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.detect(
            ["invalid"],
            detected_at=BASE_TIME,
        )


def test_condition_metadata_preserves_governance():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    condition = result.conditions[0]

    assert condition.metadata["source"] == "M37.3"
    assert condition.metadata["read_only"] is True
    assert condition.metadata["executable"] is False
    assert (
        condition.metadata["requires_human_approval"]
        is True
    )


def test_runtime_result_is_non_executable():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    result = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    assert result.read_only is True
    assert result.executable is False
    assert result.requires_human_approval is True


def test_reset_allows_reprocessing():
    runtime = BackgroundConditionRuntime()
    runtime.start()

    first = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.detect(
        [decision()],
        detected_at=BASE_TIME,
    )

    assert first.detected_conditions == 1
    assert second.detected_conditions == 1


def test_custom_severity_configuration():
    runtime = BackgroundConditionRuntime(
        warning_event_types={"custom.warning"},
        critical_event_types={"custom.critical"},
    )
    runtime.start()

    result = runtime.detect(
        [
            decision("evt-1", "custom.warning"),
            decision("evt-2", "custom.critical"),
        ],
        detected_at=BASE_TIME,
    )

    assert result.detected_conditions == 2
    assert result.conditions[0].severity == ConditionSeverity.WARNING
    assert result.conditions[1].severity == ConditionSeverity.CRITICAL
