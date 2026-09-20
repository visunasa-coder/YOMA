from datetime import datetime, timezone

import pytest

from yoma.office.integration import IntegrationEventBridge
from yoma.office.operations import OperationalEventBus


def test_bridge_normalizes_record():
    bridge = IntegrationEventBridge()

    event = bridge.normalize(
        source="generic_attendance",
        event_type="attendance.check_in",
        record={
            "id": "ATT001",
            "employee_id": "EMP001",
            "timestamp": "2026-09-03T09:00:00+05:30",
        },
        user_id="EMP001",
        occurred_at="2026-09-03T09:00:00+05:30",
    )

    assert event.event_id == "ATT001"
    assert event.event_type == "attendance.check_in"
    assert event.source == "generic_attendance"
    assert event.user_id == "EMP001"
    assert event.data["employee_id"] == "EMP001"


def test_bridge_accepts_datetime():
    bridge = IntegrationEventBridge()

    timestamp = datetime.now(timezone.utc)

    event = bridge.normalize(
        source="test",
        event_type="test.event",
        record={"id": "EV001"},
        occurred_at=timestamp,
    )

    assert event.occurred_at == timestamp


def test_bridge_uses_record_id():
    bridge = IntegrationEventBridge()

    event = bridge.normalize(
        source="test",
        event_type="test.event",
        record={"id": "REC001"},
    )

    assert event.event_id == "REC001"


def test_bridge_requires_event_id():
    bridge = IntegrationEventBridge()

    with pytest.raises(ValueError):
        bridge.normalize(
            source="test",
            event_type="test.event",
            record={"value": 1},
        )


def test_bridge_requires_source():
    bridge = IntegrationEventBridge()

    with pytest.raises(ValueError):
        bridge.normalize(
            source="",
            event_type="test.event",
            record={"id": "EV001"},
        )


def test_bridge_requires_event_type():
    bridge = IntegrationEventBridge()

    with pytest.raises(ValueError):
        bridge.normalize(
            source="test",
            event_type="",
            record={"id": "EV001"},
        )


def test_bridge_ingest_publishes_event():
    bus = OperationalEventBus()
    received = []

    bus.subscribe(received.append)

    bridge = IntegrationEventBridge(bus)

    event = bridge.ingest(
        source="calendar",
        event_type="calendar.event",
        record={"id": "CAL001", "title": "Meeting"},
    )

    assert event in received
    assert received[0].event_id == "CAL001"


def test_bridge_ingest_many():
    bus = OperationalEventBus()
    received = []

    bus.subscribe(received.append)

    bridge = IntegrationEventBridge(bus)

    events = bridge.ingest_many(
        [
            {"id": "EV001"},
            {"id": "EV002"},
            {"id": "EV003"},
        ],
        source="test",
        event_type="test.event",
    )

    assert len(events) == 3
    assert received == events


def test_bridge_copies_record_data():
    bridge = IntegrationEventBridge()

    record = {
        "id": "EV001",
        "employee_id": "EMP001",
        "department": "Engineering",
    }

    event = bridge.normalize(
        source="hrms",
        event_type="employee.updated",
        record=record,
    )

    record["department"] = "Changed"

    assert event.data["department"] == "Engineering"
