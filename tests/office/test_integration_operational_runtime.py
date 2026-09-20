from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.adapters.runtime import AdapterRuntimeManager
from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.integration_operational_runtime import (
    IntegrationOperationalResult,
    IntegrationOperationalRuntime,
)
from yoma.office.intelligence.operational_bus_runtime import (
    OperationalBusIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.rules import high_workload_rule
from yoma.office.integration import Integration, IntegrationRuntimeManager
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent, OperationalEventBus
from yoma.office.adapters import YomaAdapter


class RuntimeAdapter(YomaAdapter):
    name = "m26_runtime"
    category = "test"

    def __init__(self, events):
        super().__init__()
        self.events = list(events)

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
        if not self.connected:
            raise RuntimeError("not connected")
        return list(self.events)


def make_event(event_id="m26-event-1"):
    return OperationalEvent(
        event_id=event_id,
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="org-1",
        user_id="emp-1",
        source="m26_runtime",
        severity="high",
        data={"score": 0.9},
    )


def make_runtime(events):
    integration = IntegrationRuntimeManager()

    integration.register(
        Integration(
            "m26_runtime",
            "test_provider",
            "test",
        ),
        RuntimeAdapter(events),
    )

    integration.configure(
        "m26_runtime",
        {"endpoint": "test"},
    )

    integration.connect("m26_runtime")

    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    organization = Organization(
        organization_id="org-1",
        name="Test Org",
    )

    employee = Employee(
        employee_id="emp-1",
        name="Employee One",
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

    runtime = IntegrationOperationalRuntime(
        integration_runtime=integration,
        bus_runtime=bus_runtime,
    )

    return runtime, integration, bus_runtime, bus


def test_constructor_validates_dependencies():
    with pytest.raises(TypeError):
        IntegrationOperationalRuntime(
            integration_runtime=object(),
            bus_runtime=object(),
        )


def test_start_and_stop_delegate_to_bus_runtime():
    runtime, _, bus_runtime, _ = make_runtime([])

    assert bus_runtime.running is False

    runtime.start()

    assert bus_runtime.running is True

    runtime.stop()

    assert bus_runtime.running is False


def test_collect_bridges_integration_events_to_intelligence():
    runtime, _, _, _ = make_runtime([make_event()])

    runtime.start()

    result = runtime.collect("m26_runtime")

    assert isinstance(result, IntegrationOperationalResult)
    assert result.adapter == "m26_runtime"
    assert len(result.events) == 1
    assert len(result.intelligence_results) == 1


def test_collected_event_reaches_full_m25_pipeline():
    runtime, _, _, _ = make_runtime([make_event()])

    runtime.start()

    result = runtime.collect("m26_runtime")
    intelligence = result.intelligence_results[0].intelligence

    assert len(intelligence.events) == 1
    assert len(intelligence.signals) == 1
    assert len(intelligence.situations) == 1
    assert len(intelligence.contexts) == 1


def test_collection_requires_connected_integration():
    runtime, integration, _, _ = make_runtime([])

    integration.disconnect("m26_runtime")

    with pytest.raises(RuntimeError, match="not connected"):
        runtime.collect("m26_runtime")


def test_empty_collection_is_safe():
    runtime, _, _, bus = make_runtime([])

    runtime.start()

    result = runtime.collect("m26_runtime")

    assert result.events == ()
    assert result.intelligence_results == ()
    assert bus.subscriber_count == 1


def test_stop_prevents_intelligence_processing():
    runtime, _, _, bus = make_runtime([make_event()])

    runtime.start()
    runtime.stop()

    runtime.integration_runtime.collect("m26_runtime")

    assert bus.subscriber_count == 1


def test_last_result_tracks_collection():
    runtime, _, _, _ = make_runtime([make_event()])

    runtime.start()

    assert runtime.last_result is None

    result = runtime.collect("m26_runtime")

    assert runtime.last_result is result


def test_close_unsubscribes_bus_runtime():
    runtime, _, bus_runtime, bus = make_runtime([])

    runtime.start()
    runtime.close()

    assert bus_runtime.subscribed is False
    assert bus.subscriber_count == 0


def test_collect_all_processes_integrations():
    runtime, integration, _, _ = make_runtime([make_event()])

    second_adapter = RuntimeAdapter([])
    second_adapter.name = "m26_runtime_2"

    integration.register(
        Integration(
            "m26_runtime_2",
            "test_provider",
            "test",
        ),
        second_adapter,
    )

    integration.configure(
        "m26_runtime_2",
        {"endpoint": "test"},
    )

    integration.connect("m26_runtime_2")

    runtime.start()

    results, adapter_results = runtime.collect_all()

    assert len(results) == 2
    assert len(adapter_results) == 2
    assert results[0].adapter == "m26_runtime"
    assert results[1].adapter == "m26_runtime_2"
