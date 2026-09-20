from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.adapters.base import YomaAdapter
from yoma.office.adapters.runtime import (
    AdapterRuntimeManager,
    AdapterRuntimeResult,
)
from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.rules import high_workload_rule
from yoma.office.intelligence.integration_intelligence_runtime import (
    IntegrationIntelligenceResult,
    IntegrationIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent, OperationalEventBus


class FakeAdapter(YomaAdapter):
    name = "fake"
    category = "test"

    def __init__(self, events):
        super().__init__()
        self.events = list(events)

    def health(self):
        return {"connected": True, "status": "healthy"}

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        return list(self.events)


def make_event(event_id="evt-1"):
    return OperationalEvent(
        event_id=event_id,
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="org-1",
        user_id="emp-1",
        source="fake",
        severity="high",
        data={"score": 0.9},
    )


def make_runtime(events):
    adapter_runtime = AdapterRuntimeManager()
    adapter = FakeAdapter(events)
    adapter_runtime.register(adapter)

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

    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    intelligence_runtime = OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )

    bus = OperationalEventBus()

    runtime = IntegrationIntelligenceRuntime(
        adapter_runtime=adapter_runtime,
        intelligence_runtime=intelligence_runtime,
        event_bus=bus,
    )

    return runtime, adapter_runtime, bus


def test_collect_bridges_adapter_events_into_unified_intelligence():
    event = make_event()

    runtime, _, bus = make_runtime([event])

    received = []
    bus.subscribe(received.append)

    result = runtime.collect("fake")

    assert isinstance(result, IntegrationIntelligenceResult)
    assert result.adapter == "fake"
    assert result.events == (event,)
    assert result.adapter_result.status == "collected"
    assert result.adapter_result.events_collected == 1

    assert result.intelligence.events == (event,)
    assert len(received) == 1
    assert received[0] == event


def test_unified_pipeline_is_preserved():
    runtime, _, _ = make_runtime([make_event()])

    result = runtime.collect("fake")

    assert len(result.intelligence.events) == 1
    assert len(result.intelligence.signals) == 1
    assert len(result.intelligence.situations) == 1
    assert len(result.intelligence.contexts) == 1


def test_empty_adapter_collection_is_safe():
    runtime, _, bus = make_runtime([])

    received = []
    bus.subscribe(received.append)

    result = runtime.collect("fake")

    assert result.events == ()
    assert result.adapter_result.events_collected == 0
    assert result.intelligence.events == ()
    assert result.intelligence.signals == ()
    assert result.intelligence.situations == ()
    assert result.intelligence.patterns == ()
    assert result.intelligence.decisions == ()
    assert received == []


def test_process_events_validates_event_types():
    runtime, _, _ = make_runtime([])

    adapter_result = AdapterRuntimeResult(
        adapter="fake",
        status="collected",
    )

    with pytest.raises(TypeError):
        runtime.process_events(
            "fake",
            [object()],
            adapter_result,
        )


def test_process_events_validates_adapter_result():
    runtime, _, _ = make_runtime([])

    with pytest.raises(TypeError):
        runtime.process_events(
            "fake",
            [],
            object(),
        )


def test_last_result_tracks_latest_collection():
    event = make_event()

    runtime, _, _ = make_runtime([event])

    assert runtime.last_result is None

    result = runtime.collect("fake")

    assert runtime.last_result is result


def test_collect_all_processes_registered_adapters():
    event = make_event()

    runtime, adapter_runtime, _ = make_runtime([event])

    second = FakeAdapter([])
    second.name = "fake-2"
    adapter_runtime.register(second)

    results, adapter_results = runtime.collect_all()

    assert len(results) == 2
    assert len(adapter_results) == 2
    assert results[0].adapter == "fake"
    assert results[1].adapter == "fake-2"


def test_constructor_validates_dependencies():
    with pytest.raises(TypeError):
        IntegrationIntelligenceRuntime(
            adapter_runtime=object(),
            intelligence_runtime=object(),
        )
