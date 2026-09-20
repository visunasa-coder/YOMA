from datetime import datetime, timezone

from yoma.office.adapters.base import YomaAdapter
from yoma.office.integration import (
    AdapterEventCollector,
    IntegrationEventBridge,
)
from yoma.office.operations import OperationalEvent


class AttendanceTestAdapter(YomaAdapter):
    name = "test_attendance"
    category = "attendance"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return ["attendance_events"]

    def connect(self, config):
        pass

    def disconnect(self):
        pass


class UniversalEventAdapter(YomaAdapter):
    name = "test_universal"
    category = "test"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        pass

    def disconnect(self):
        pass

    def collect_events(self):
        return [
            OperationalEvent(
                event_id="EV001",
                event_type="test.event",
                occurred_at=datetime.now(timezone.utc),
                source=self.name,
            )
        ]


def test_collect_records():
    received = []

    bridge = IntegrationEventBridge()
    bridge.bus.subscribe(received.append)

    collector = AdapterEventCollector(bridge)

    adapter = AttendanceTestAdapter()

    events = collector.collect(
        adapter,
        event_type="attendance.check_in",
        records=[
            {
                "id": "ATT001",
                "employee_id": "EMP001",
            },
            {
                "id": "ATT002",
                "employee_id": "EMP002",
            },
        ],
        user_id_field="employee_id",
    )

    assert len(events) == 2
    assert events[0].source == "test_attendance"
    assert events[0].user_id == "EMP001"
    assert events[1].user_id == "EMP002"
    assert received == events


def test_collect_system_records():
    bridge = IntegrationEventBridge()
    collector = AdapterEventCollector(bridge)

    adapter = AttendanceTestAdapter()

    events = collector.collect(
        adapter,
        event_type="hardware.device",
        records=[
            {
                "id": "DEV001",
                "system_id": "SYS001",
            }
        ],
        system_id_field="system_id",
    )

    assert events[0].system_id == "SYS001"


def test_collect_empty_records():
    bridge = IntegrationEventBridge()
    collector = AdapterEventCollector(bridge)

    events = collector.collect(
        AttendanceTestAdapter(),
        event_type="attendance.event",
        records=[],
    )

    assert events == []


def test_collect_universal_adapter_events():
    received = []

    bridge = IntegrationEventBridge()
    bridge.bus.subscribe(received.append)

    collector = AdapterEventCollector(bridge)

    events = collector.collect_adapter_events(
        UniversalEventAdapter()
    )

    assert len(events) == 1
    assert events[0].event_id == "EV001"
    assert received == events
