from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.control_server.agent import ControlServerAgent
from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
)
from yoma.office.intelligence.control_server_operational_intelligence import (
    ControlServerOperationalIntelligence,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.models.organization import Employee, Organization
from yoma.office.intelligence.organization_graph import OrganizationGraph
from yoma.office.operations import OperationalEvent
from yoma.office.runtime import YomaEmbeddedRuntime


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


def make_components():
    agent = ControlServerAgent()
    embedded = YomaEmbeddedRuntime()

    return agent, embedded


def make_event() -> OperationalEvent:
    return OperationalEvent(
        event_id="M27.3-EVENT",
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


def make_runtime():
    agent, embedded = make_components()

    return ControlServerOperationalIntelligence(
        agent=agent,
        embedded_runtime=embedded,
        intelligence_runtime=make_intelligence(),
    )


def test_start_starts_intelligence_bridge():
    runtime = make_runtime()

    assert runtime.running is False
    assert runtime.subscribed is False

    runtime.start()

    assert runtime.running is True
    assert runtime.subscribed is True

    runtime.close()


def test_start_is_idempotent():
    runtime = make_runtime()

    runtime.start()
    runtime.start()

    assert runtime.running is True
    assert runtime.subscribed is True

    runtime.close()


def test_stop_disables_processing_but_keeps_subscription():
    runtime = make_runtime()

    runtime.start()
    runtime.stop()

    assert runtime.running is False
    assert runtime.subscribed is True

    runtime.close()


def test_close_unsubscribes():
    runtime = make_runtime()

    runtime.start()
    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False


def test_embedded_runtime_bus_is_used():
    agent, embedded = make_components()

    runtime = ControlServerOperationalIntelligence(
        agent=agent,
        embedded_runtime=embedded,
        intelligence_runtime=make_intelligence(),
    )

    assert runtime.bridge.bus_runtime.event_bus is embedded.bus

    runtime.close()


def test_event_flows_through_existing_embedded_bus():
    agent, embedded = make_components()

    runtime = ControlServerOperationalIntelligence(
        agent=agent,
        embedded_runtime=embedded,
        intelligence_runtime=make_intelligence(),
    )

    runtime.start()
    embedded.start()

    event = make_event()
    embedded.publish(event)

    result = runtime.last_result

    assert result is not None
    assert result.event == event
    assert result.intelligence.events == (event,)
    assert len(result.intelligence.signals) == 1

    embedded.stop()
    runtime.close()


def test_invalid_agent_is_rejected():
    _, embedded = make_components()

    with pytest.raises(TypeError):
        ControlServerOperationalIntelligence(
            agent=object(),
            embedded_runtime=embedded,
            intelligence_runtime=make_intelligence(),
        )


def test_invalid_embedded_runtime_is_rejected():
    agent, _ = make_components()

    with pytest.raises(TypeError):
        ControlServerOperationalIntelligence(
            agent=agent,
            embedded_runtime=object(),
            intelligence_runtime=make_intelligence(),
        )


def test_invalid_intelligence_runtime_is_rejected():
    agent, embedded = make_components()

    with pytest.raises(TypeError):
        ControlServerOperationalIntelligence(
            agent=agent,
            embedded_runtime=embedded,
            intelligence_runtime=object(),
        )


def test_lifecycle_can_be_closed_without_start():
    runtime = make_runtime()

    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False
