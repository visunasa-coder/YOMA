from __future__ import annotations

from datetime import datetime, timezone

import pytest

from yoma.office.control_server.agent import ControlServerAgent
from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.intelligence import (
    OperationalIntelligenceEngine,
    high_workload_rule,
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
        event_id="M27.6-EVENT",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id="EMP001",
        system_id=None,
        source="m27.6-test",
        severity="warning",
        data={"score": 0.9},
    )


def test_runtime_accepts_intelligence_runtime():
    intelligence = make_intelligence()

    runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        port=0,
    )

    assert runtime.agent.intelligence_runtime is intelligence

    runtime.stop()


def test_runtime_preserves_same_intelligence_instance():
    intelligence = make_intelligence()

    runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        port=0,
    )

    assert runtime.agent.intelligence_runtime is intelligence
    assert runtime.agent.intelligence_runtime is not None

    runtime.stop()


def test_runtime_status_exposes_intelligence():
    intelligence = make_intelligence()

    runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        port=0,
    )

    status = runtime.status()

    assert "intelligence" in status
    assert status["intelligence"]["available"] is True
    assert status["intelligence"]["has_latest_result"] is False

    runtime.stop()


def test_runtime_status_reflects_processed_intelligence():
    intelligence = make_intelligence()
    intelligence.process([make_event()])

    runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        port=0,
    )

    status = runtime.status()

    assert status["intelligence"]["available"] is True
    assert status["intelligence"]["has_latest_result"] is True
    assert status["intelligence"]["event_count"] == 1
    assert status["intelligence"]["signal_count"] == 1

    runtime.stop()


def test_runtime_without_intelligence_remains_compatible():
    runtime = ControlServerRuntime(port=0)

    status = runtime.status()

    assert status["intelligence"]["available"] is False
    assert status["intelligence"]["has_latest_result"] is False

    runtime.stop()


def test_existing_agent_can_be_bound_to_intelligence():
    agent = ControlServerAgent()
    intelligence = make_intelligence()

    runtime = ControlServerRuntime(
        agent=agent,
        intelligence_runtime=intelligence,
        port=0,
    )

    assert runtime.agent is agent
    assert agent.intelligence_runtime is intelligence

    runtime.stop()


def test_conflicting_agent_intelligence_is_rejected():
    agent = ControlServerAgent(
        intelligence_runtime=make_intelligence(),
    )

    intelligence = make_intelligence()

    with pytest.raises(ValueError):
        ControlServerRuntime(
            agent=agent,
            intelligence_runtime=intelligence,
            port=0,
        )


def test_invalid_intelligence_runtime_is_rejected():
    with pytest.raises(TypeError):
        ControlServerRuntime(
            intelligence_runtime=object(),
            port=0,
        )


def test_runtime_api_uses_bound_intelligence():
    intelligence = make_intelligence()

    runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        port=0,
    )

    response = runtime.app.routes

    paths = {
        route.path
        for route in response
        if hasattr(route, "path")
    }

    assert "/intelligence/status" in paths
    assert "/intelligence/latest" in paths

    runtime.stop()


def test_intelligence_binding_does_not_replace_embedded_runtime():
    intelligence = make_intelligence()

    runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        port=0,
    )

    embedded = runtime.embedded_runtime

    assert runtime.embedded_runtime is embedded
    assert runtime.agent.intelligence_runtime is intelligence

    runtime.stop()
