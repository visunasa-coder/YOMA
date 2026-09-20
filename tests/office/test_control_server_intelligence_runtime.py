from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.intelligence.control_server_intelligence_runtime import (
    ControlServerIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.models.organization import Employee, Organization
from yoma.office.operations import OperationalEvent


def make_intelligence() -> OperationalUnifiedRuntime:
    organization = Organization(
        organization_id="ORG001",
        name="YOMA Test Org",
    )

    employee = Employee(
        employee_id="EMP001",
        name="Test Employee",
        organization_id="ORG001",
    )

    graph = OrganizationGraph(
        organizations=[organization],
        employees=[employee],
    )

    engine = OperationalIntelligenceEngine()
    engine.register_rule("workload", high_workload_rule)

    return OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )


def make_event() -> OperationalEvent:
    return OperationalEvent(
        event_id="M27.4-EVENT",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id="EMP001",
        system_id=None,
        source="test",
        location_id=None,
        severity="warning",
        data={"score": 0.9},
    )


def make_runtime() -> ControlServerRuntime:
    return ControlServerRuntime(
        host="127.0.0.1",
        port=18766,
    )


def make_intelligence_runtime() -> ControlServerIntelligenceRuntime:
    return ControlServerIntelligenceRuntime(
        control_server_runtime=make_runtime(),
        intelligence_runtime=make_intelligence(),
    )


def test_runtime_uses_existing_control_server_runtime():
    control = make_runtime()

    runtime = ControlServerIntelligenceRuntime(
        control_server_runtime=control,
        intelligence_runtime=make_intelligence(),
    )

    assert runtime.control_server_runtime is control
    assert runtime.embedded_runtime is control.embedded_runtime
    assert runtime.agent is control.agent

    runtime.close()


def test_existing_embedded_bus_is_reused():
    control = make_runtime()

    runtime = ControlServerIntelligenceRuntime(
        control_server_runtime=control,
        intelligence_runtime=make_intelligence(),
    )

    assert runtime.bridge.bus_runtime.event_bus is control.embedded_runtime.bus

    runtime.close()


def test_starts_intelligence_before_control_server():
    runtime = make_intelligence_runtime()

    assert runtime.running is False
    assert runtime.subscribed is False
    assert runtime.control_server_runtime.running is False

    runtime.start()

    assert runtime.running is True
    assert runtime.subscribed is True
    assert runtime.control_server_runtime.running is True
    assert runtime.control_server_runtime.embedded_runtime.running is True

    runtime.close()


def test_start_is_idempotent():
    runtime = make_intelligence_runtime()

    runtime.start()
    runtime.start()

    assert runtime.running is True
    assert runtime.subscribed is True
    assert runtime.control_server_runtime.running is True

    runtime.close()


def test_event_flows_through_control_server_embedded_runtime():
    runtime = make_intelligence_runtime()

    runtime.start()

    event = make_event()

    runtime.embedded_runtime.publish(event)

    result = runtime.last_result

    assert result is not None
    assert result.event == event
    assert result.intelligence.events == (event,)
    assert len(result.intelligence.signals) == 1

    runtime.close()


def test_stop_stops_control_server_and_intelligence():
    runtime = make_intelligence_runtime()

    runtime.start()
    runtime.stop()

    assert runtime.running is False
    assert runtime.subscribed is True
    assert runtime.control_server_runtime.running is False
    assert runtime.embedded_runtime.running is False


def test_close_unsubscribes_intelligence():
    runtime = make_intelligence_runtime()

    runtime.start()
    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False
    assert runtime.control_server_runtime.running is False


def test_close_without_start_is_safe():
    runtime = make_intelligence_runtime()

    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False
    assert runtime.control_server_runtime.running is False


def test_invalid_control_server_runtime_is_rejected():
    with pytest.raises(TypeError):
        ControlServerIntelligenceRuntime(
            control_server_runtime=object(),
            intelligence_runtime=make_intelligence(),
        )


def test_invalid_intelligence_runtime_is_rejected():
    with pytest.raises(TypeError):
        ControlServerIntelligenceRuntime(
            control_server_runtime=make_runtime(),
            intelligence_runtime=object(),
        )
