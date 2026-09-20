from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.background_intelligence import (
    BackgroundEvent,
    BackgroundIntelligenceState,
)
from yoma.office.intelligence.background_trigger import (
    BackgroundTriggerDecision,
    BackgroundTriggerResult,
    BackgroundTriggerRuntime,
    TriggerEligibility,
)


BASE_TIME = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def event(
    event_id="evt-1",
    event_type="ticket.updated",
    source_system="jira",
):
    return BackgroundEvent(
        event_id=event_id,
        event_type=event_type,
        occurred_at=BASE_TIME,
        source_system=source_system,
        entity_id="ticket-1",
    )


def test_initial_state_is_stopped():
    runtime = BackgroundTriggerRuntime()

    assert runtime.state == BackgroundIntelligenceState.STOPPED
    assert runtime.running is False
    assert runtime.executable is False
    assert runtime.requires_human_approval is True


def test_start_and_stop():
    runtime = BackgroundTriggerRuntime()

    runtime.start()
    assert runtime.running is True

    runtime.stop()
    assert runtime.running is False


def test_evaluation_requires_running_runtime():
    runtime = BackgroundTriggerRuntime()

    with pytest.raises(RuntimeError, match="not running"):
        runtime.evaluate([event()], evaluated_at=BASE_TIME)


def test_eligible_event_produces_work_item():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    result = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    assert isinstance(result, BackgroundTriggerResult)
    assert result.processed_events == 1
    assert result.eligible_events == 1
    assert result.ineligible_events == 0

    assert result.decisions[0].eligibility == TriggerEligibility.ELIGIBLE
    assert result.decisions[0].eligible is True

    assert len(result.work_items) == 1
    assert result.work_items[0].event_id == "evt-1"


def test_event_type_filter_marks_event_ineligible():
    runtime = BackgroundTriggerRuntime(
        event_types={"ticket.updated"}
    )
    runtime.start()

    result = runtime.evaluate(
        [event("evt-1", "ticket.closed")],
        evaluated_at=BASE_TIME,
    )

    assert result.eligible_events == 0
    assert result.ineligible_events == 1
    assert result.work_items == ()
    assert result.decisions[0].reason == "event_type_not_eligible"


def test_source_system_filter_marks_event_ineligible():
    runtime = BackgroundTriggerRuntime(
        source_systems={"salesforce"}
    )
    runtime.start()

    result = runtime.evaluate(
        [event("evt-1", source_system="jira")],
        evaluated_at=BASE_TIME,
    )

    assert result.eligible_events == 0
    assert result.ineligible_events == 1
    assert result.work_items == ()
    assert result.decisions[0].reason == "source_system_not_eligible"


def test_multiple_filters_require_both_conditions():
    runtime = BackgroundTriggerRuntime(
        event_types={"ticket.updated"},
        source_systems={"jira"},
    )
    runtime.start()

    result = runtime.evaluate(
        [
            event("evt-1", "ticket.updated", "jira"),
            event("evt-2", "ticket.closed", "jira"),
            event("evt-3", "ticket.updated", "salesforce"),
        ],
        evaluated_at=BASE_TIME,
    )

    assert result.processed_events == 3
    assert result.eligible_events == 1
    assert result.ineligible_events == 2
    assert [item.event_id for item in result.work_items] == ["evt-1"]


def test_duplicate_event_is_not_reprocessed():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    first = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    second = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    assert first.eligible_events == 1
    assert second.processed_events == 0
    assert second.work_items == ()


def test_results_are_deterministic():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    result = runtime.evaluate(
        [
            event("evt-2"),
            event("evt-1"),
        ],
        evaluated_at=BASE_TIME,
    )

    assert [decision.event_id for decision in result.decisions] == [
        "evt-1",
        "evt-2",
    ]

    assert [item.event_id for item in result.work_items] == [
        "evt-1",
        "evt-2",
    ]


def test_timezone_is_required():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    with pytest.raises(ValueError, match="timezone-aware"):
        runtime.evaluate(
            [event()],
            evaluated_at=datetime(2026, 9, 6, 12, 0),
        )


def test_invalid_event_type_is_rejected():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    with pytest.raises(TypeError):
        runtime.evaluate(["invalid"], evaluated_at=BASE_TIME)


def test_work_items_remain_non_executable():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    result = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    item = result.work_items[0]

    assert result.read_only is True
    assert result.executable is False
    assert item.requires_human_approval is True
    assert item.executable is False


def test_decision_metadata_identifies_m37_2():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    result = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    decision = result.decisions[0]

    assert isinstance(decision, BackgroundTriggerDecision)
    assert decision.metadata["source"] == "M37.2"
    assert decision.metadata["read_only"] is True
    assert decision.metadata["executable"] is False


def test_reset_allows_reprocessing():
    runtime = BackgroundTriggerRuntime()
    runtime.start()

    first = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    runtime.reset()

    second = runtime.evaluate(
        [event()],
        evaluated_at=BASE_TIME,
    )

    assert first.eligible_events == 1
    assert second.eligible_events == 1
