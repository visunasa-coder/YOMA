from datetime import datetime, timezone

import pytest

from yoma.office.adapters import (
    AdapterCollectionScheduler,
    AdapterRuntimeManager,
    YomaAdapter,
)
from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.operational_bus_runtime import (
    OperationalBusIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.rules import high_workload_rule
from yoma.office.intelligence.scheduled_operational_intelligence import (
    ScheduledOperationalIntelligence,
    ScheduledIntelligenceResult,
)
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent, OperationalEventBus


class ScheduledAdapter(YomaAdapter):
    name = "scheduled_test"
    category = "test"

    def __init__(self):
        super().__init__()
        self.collection_count = 0

    def health(self):
        return {
            "status": "healthy",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        self.collection_count += 1

        return [
            OperationalEvent(
                event_id=f"SCHED-{self.collection_count}",
                event_type="workload.high",
                occurred_at=datetime.now(timezone.utc),
                organization_id="org-1",
                user_id="emp-1",
                source=self.name,
                severity="high",
                data={"score": 0.9},
            )
        ]


def make_bridge():
    manager = AdapterRuntimeManager()
    adapter = ScheduledAdapter()

    manager.register(adapter)
    manager.connect("scheduled_test", {})

    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    organization = Organization(
        organization_id="org-1",
        name="Test Organization",
    )

    employee = Employee(
        employee_id="emp-1",
        name="Test Employee",
        organization_id="org-1",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    unified = OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )

    bus = OperationalEventBus()

    bus_runtime = OperationalBusIntelligenceRuntime(
        intelligence_runtime=unified,
        event_bus=bus,
    )

    bridge = ScheduledOperationalIntelligence(
        scheduler=AdapterCollectionScheduler(
            manager,
            interval=60,
        ),
        bus_runtime=bus_runtime,
    )

    return bridge, adapter, bus


def test_constructor_validates_scheduler():
    with pytest.raises(TypeError):
        ScheduledOperationalIntelligence(
            scheduler=object(),
            bus_runtime=object(),
        )


def test_constructor_validates_bus_runtime():
    bridge, _, _ = make_bridge()

    assert bridge.scheduler is not None


def test_handle_events_forwards_events_to_intelligence():
    bridge, _, _ = make_bridge()

    bridge.bus_runtime.start()

    event = OperationalEvent(
        event_id="DIRECT-1",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="org-1",
        user_id="emp-1",
        source="test",
        severity="high",
        data={"score": 0.9},
    )

    result = bridge.handle_events([event])

    assert isinstance(result, ScheduledIntelligenceResult)
    assert len(result.events) == 1
    assert len(result.intelligence_results) == 1


def test_scheduler_cycle_reaches_intelligence():
    bridge, adapter, _ = make_bridge()

    bridge.bus_runtime.start()

    bridge.scheduler.on_events = bridge.handle_events

    bridge.scheduler.run_once()

    assert adapter.collection_count == 1
    assert bridge.last_result is not None
    assert len(bridge.last_result.events) == 1
    assert len(bridge.last_result.intelligence_results) == 1

    intelligence = bridge.last_result.intelligence_results[0].intelligence

    assert len(intelligence.events) == 1
    assert len(intelligence.signals) == 1
    assert len(intelligence.situations) == 1


def test_scheduler_status_remains_owned_by_scheduler():
    bridge, _, _ = make_bridge()

    bridge.bus_runtime.start()
    bridge.scheduler.on_events = bridge.handle_events

    bridge.scheduler.run_once()

    status = bridge.scheduler.status()

    assert status.cycle_count == 1
    assert status.events_collected == 1


def test_empty_scheduler_cycle_is_safe():
    manager = AdapterRuntimeManager()

    engine = OperationalIntelligenceEngine()

    graph = OrganizationGraph()

    unified = OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )

    bus = OperationalEventBus()

    bus_runtime = OperationalBusIntelligenceRuntime(
        intelligence_runtime=unified,
        event_bus=bus,
    )

    bridge = ScheduledOperationalIntelligence(
        scheduler=AdapterCollectionScheduler(
            manager,
            interval=60,
        ),
        bus_runtime=bus_runtime,
    )

    bus_runtime.start()

    result = bridge.handle_events([])

    assert result.events == ()
    assert result.intelligence_results == ()


def test_invalid_scheduled_event_is_rejected():
    bridge, _, _ = make_bridge()

    bridge.bus_runtime.start()

    with pytest.raises(TypeError):
        bridge.handle_events([object()])


def test_last_result_tracks_latest_cycle():
    bridge, _, _ = make_bridge()

    bridge.bus_runtime.start()

    bridge.scheduler.on_events = bridge.handle_events

    bridge.scheduler.run_once()
    first = bridge.last_result

    bridge.scheduler.run_once()
    second = bridge.last_result

    assert first is not None
    assert second is not None
    assert second is not first
    assert len(second.events) == 1


def test_stop_stops_scheduler_and_intelligence():
    bridge, _, _ = make_bridge()

    bridge.start()

    assert bridge.scheduler.running is True
    assert bridge.bus_runtime.running is True

    bridge.stop()

    assert bridge.scheduler.running is False
    assert bridge.bus_runtime.running is False


def test_close_unsubscribes_intelligence():
    bridge, _, bus = make_bridge()

    bridge.start()
    bridge.close()

    assert bridge.scheduler.running is False
    assert bridge.bus_runtime.subscribed is False
    assert bus.subscriber_count == 0
