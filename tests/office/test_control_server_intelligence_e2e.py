from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

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
        name="YOMA E2E Org",
    )

    employee = Employee(
        employee_id="EMP001",
        name="E2E Employee",
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
        event_id="M27.7-E2E-001",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="ORG001",
        user_id="EMP001",
        system_id=None,
        source="m27.7-e2e",
        severity="warning",
        data={"score": 0.95},
    )


def make_runtime() -> ControlServerIntelligenceRuntime:
    intelligence = make_intelligence()

    control_runtime = ControlServerRuntime(
        intelligence_runtime=intelligence,
        host="127.0.0.1",
        port=0,
    )

    return ControlServerIntelligenceRuntime(
        control_server_runtime=control_runtime,
        intelligence_runtime=intelligence,
    )


def test_control_server_intelligence_runtime_is_composed():
    runtime = make_runtime()

    assert runtime.control_server_runtime is not None
    assert runtime.agent is runtime.control_server_runtime.agent
    assert runtime.embedded_runtime is (
        runtime.control_server_runtime.embedded_runtime
    )

    runtime.close()


def test_same_intelligence_runtime_is_shared():
    runtime = make_runtime()

    assert (
        runtime.agent.intelligence_runtime
        is runtime.bridge.intelligence_runtime
    )

    runtime.close()


def test_canonical_event_bus_is_reused():
    runtime = make_runtime()

    assert (
        runtime.bridge.bus_runtime.event_bus
        is runtime.embedded_runtime.bus
    )

    runtime.close()


def test_start_activates_control_server_and_intelligence():
    runtime = make_runtime()

    try:
        assert runtime.running is False
        assert runtime.subscribed is False
        assert runtime.control_server_runtime.running is False

        runtime.start()

        assert runtime.running is True
        assert runtime.subscribed is True
        assert runtime.control_server_runtime.running is True
        assert runtime.agent.running is True
        assert runtime.embedded_runtime.running is True
    finally:
        runtime.close()


def test_event_enters_through_real_embedded_runtime():
    runtime = make_runtime()

    try:
        runtime.start()

        event = make_event()

        runtime.embedded_runtime.publish(event)

        result = runtime.last_result

        assert result is not None
        assert result.event == event
        assert result.intelligence.events == (event,)

        assert runtime.agent.intelligence_latest() is not None
        assert runtime.agent.intelligence_latest() is (
            runtime.agent.intelligence_runtime.last_result
        )
    finally:
        runtime.close()


def test_event_generates_operational_signal():
    runtime = make_runtime()

    try:
        runtime.start()

        runtime.embedded_runtime.publish(make_event())

        result = runtime.last_result

        assert result is not None
        assert len(result.intelligence.signals) == 1
        assert result.intelligence.signals[0].signal_id == (
            "SIG-M27.7-E2E-001"
        )
    finally:
        runtime.close()


def test_full_operational_pipeline_is_reached():
    runtime = make_runtime()

    try:
        runtime.start()

        runtime.embedded_runtime.publish(make_event())

        result = runtime.last_result

        assert result is not None

        intelligence = result.intelligence

        assert len(intelligence.events) == 1
        assert len(intelligence.signals) == 1
        assert len(intelligence.situations) == 1
        assert len(intelligence.contexts) == 1
        assert isinstance(intelligence.patterns, tuple)
        assert isinstance(intelligence.decisions, tuple)
    finally:
        runtime.close()


def test_decisions_remain_advisory():
    runtime = make_runtime()

    try:
        runtime.start()

        runtime.embedded_runtime.publish(make_event())

        result = runtime.last_result

        assert result is not None

        for decision in result.intelligence.decisions:
            assert decision.requires_human_approval is True
            assert decision.actions == ()
    finally:
        runtime.close()


def test_status_endpoint_reflects_real_e2e_state():
    runtime = make_runtime()

    try:
        runtime.start()

        runtime.embedded_runtime.publish(make_event())

        client = TestClient(runtime.control_server_runtime.app)

        response = client.get("/status")

        assert response.status_code == 200

        data = response.json()

        assert data["intelligence"]["available"] is True
        assert data["intelligence"]["has_latest_result"] is True
        assert data["intelligence"]["event_count"] == 1
        assert data["intelligence"]["signal_count"] == 1
        assert data["intelligence"]["situation_count"] == 1
        assert data["intelligence"]["context_count"] == 1
    finally:
        runtime.close()


def test_intelligence_api_reflects_real_e2e_state():
    runtime = make_runtime()

    try:
        runtime.start()

        runtime.embedded_runtime.publish(make_event())

        client = TestClient(runtime.control_server_runtime.app)

        status = client.get("/intelligence/status")

        assert status.status_code == 200

        data = status.json()

        assert data["available"] is True
        assert data["has_latest_result"] is True
        assert data["event_count"] == 1
        assert data["signal_count"] == 1
        assert data["situation_count"] == 1
        assert data["context_count"] == 1

        latest = client.get("/intelligence/latest")

        assert latest.status_code == 200

        latest_data = latest.json()

        assert latest_data["available"] is True
        assert latest_data["has_latest_result"] is True
        assert (
            latest_data["result"]["events"][0]["event_id"]
            == "M27.7-E2E-001"
        )
        assert (
            latest_data["result"]["signals"][0]["signal_id"]
            == "SIG-M27.7-E2E-001"
        )
    finally:
        runtime.close()


def test_complete_lifecycle_stops_cleanly():
    runtime = make_runtime()

    runtime.start()
    runtime.stop()

    assert runtime.running is False
    assert runtime.control_server_runtime.running is False
    assert runtime.agent.running is False
    assert runtime.embedded_runtime.running is False
    assert runtime.subscribed is True

    runtime.close()

    assert runtime.running is False
    assert runtime.subscribed is False


def test_e2e_api_remains_read_only():
    runtime = make_runtime()

    try:
        client = TestClient(runtime.control_server_runtime.app)

        assert client.post("/status").status_code == 405
        assert client.post("/intelligence/status").status_code == 405
        assert client.post("/intelligence/latest").status_code == 405
    finally:
        runtime.close()
