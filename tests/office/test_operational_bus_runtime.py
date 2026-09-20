from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.intelligence.operational_bus_runtime import (
    BusIntelligenceResult,
    OperationalBusIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.intelligence.rules import high_workload_rule
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent, OperationalEventBus


def make_runtime():
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

    runtime = OperationalBusIntelligenceRuntime(
        intelligence_runtime=unified,
        event_bus=bus,
    )

    return runtime, bus


def make_event(event_id="evt-1"):
    return OperationalEvent(
        event_id=event_id,
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="org-1",
        user_id="emp-1",
        source="test",
        severity="high",
        data={"score": 0.9},
    )


def test_runtime_starts_stopped_and_unsubscribed():
    runtime, bus = make_runtime()

    assert runtime.running is False
    assert runtime.subscribed is False
    assert bus.subscriber_count == 0


def test_start_subscribes_and_enables_processing():
    runtime, bus = make_runtime()

    runtime.start()

    assert runtime.running is True
    assert runtime.subscribed is True
    assert bus.subscriber_count == 1


def test_bus_event_flows_through_unified_runtime():
    runtime, bus = make_runtime()

    runtime.start()

    event = make_event()
    bus.publish(event)

    result = runtime.last_result

    assert isinstance(result, BusIntelligenceResult)
    assert result.event == event
    assert result.intelligence.events == (event,)
    assert len(result.intelligence.signals) == 1
    assert len(result.intelligence.situations) == 1
    assert len(result.intelligence.contexts) == 1


def test_stopped_runtime_ignores_bus_events():
    runtime, bus = make_runtime()

    event = make_event()
    bus.publish(event)

    assert runtime.last_result is None


def test_stop_keeps_subscription_but_disables_processing():
    runtime, bus = make_runtime()

    runtime.start()
    runtime.stop()

    assert runtime.running is False
    assert runtime.subscribed is True
    assert bus.subscriber_count == 1

    bus.publish(make_event())

    assert runtime.last_result is None


def test_close_unsubscribes():
    runtime, bus = make_runtime()

    runtime.start()
    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False
    assert bus.subscriber_count == 0


def test_start_is_idempotent():
    runtime, bus = make_runtime()

    runtime.start()
    runtime.start()

    assert bus.subscriber_count == 1


def test_process_event_validates_type_and_returns_result():
    runtime, _ = make_runtime()

    with pytest.raises(TypeError):
        runtime.process_event(object())

    result = runtime.process_event(make_event())

    assert isinstance(result, BusIntelligenceResult)
    assert len(result.intelligence.signals) == 1
    assert runtime.last_result is result
