from fastapi.testclient import TestClient

from yoma.office.control_server import (
    ControlServerAgent,
    create_control_server_app,
)


def make_client():
    agent = ControlServerAgent()
    return TestClient(create_control_server_app(agent))


def test_health_endpoint():
    client = make_client()

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "yoma-control-server"
    assert data["running"] is False


def test_status_endpoint():
    client = make_client()

    response = client.get("/status")

    assert response.status_code == 200

    data = response.json()

    assert data["agent"] == "yoma-control-server"
    assert data["version"] == "0.2.0"
    assert "hostname" in data
    assert "platform" in data
    assert "hardware" in data
    assert "intelligence" in data


def test_discovery_endpoint():
    client = make_client()

    response = client.get("/discovery")

    assert response.status_code == 200

    data = response.json()

    assert "platform" in data
    assert "windows_devices" in data
    assert "serial_ports" in data
    assert "network_identity" in data


def test_hardware_endpoint():
    client = make_client()

    response = client.get("/hardware")

    assert response.status_code == 200

    data = response.json()

    assert "hardware" in data
    assert isinstance(data["hardware"], list)


def test_api_is_read_only_for_initial_endpoints():
    client = make_client()

    assert client.post("/health").status_code == 405
    assert client.post("/status").status_code == 405
    assert client.post("/discovery").status_code == 405
    assert client.post("/hardware").status_code == 405


def test_intelligence_status_without_runtime():
    client = make_client()

    response = client.get("/intelligence/status")

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "available": False,
        "has_latest_result": False,
        "event_count": 0,
        "signal_count": 0,
        "situation_count": 0,
        "context_count": 0,
        "pattern_count": 0,
        "decision_count": 0,
    }


def test_intelligence_latest_without_runtime():
    client = make_client()

    response = client.get("/intelligence/latest")

    assert response.status_code == 200

    data = response.json()

    assert data["available"] is False
    assert data["has_latest_result"] is False
    assert data["result"] is None


def test_intelligence_endpoints_are_read_only():
    client = make_client()

    assert client.post("/intelligence/status").status_code == 405
    assert client.post("/intelligence/latest").status_code == 405

def make_intelligence_runtime():
    from datetime import datetime, timezone

    from yoma.office.intelligence.engine import OperationalIntelligenceEngine
    from yoma.office.intelligence.rules import high_workload_rule
    from yoma.office.intelligence.operational_unified_runtime import (
        OperationalUnifiedRuntime,
    )
    from yoma.office.intelligence.organization_graph import OrganizationGraph
    from yoma.office.models.organization import Employee, Organization
    from yoma.office.operations import OperationalEvent

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

    runtime = OperationalUnifiedRuntime(
        intelligence_engine=engine,
        graph=graph,
    )

    event = OperationalEvent(
        event_id="evt-api-1",
        event_type="workload.high",
        occurred_at=datetime.now(timezone.utc),
        organization_id="org-1",
        user_id="emp-1",
        source="api-test",
        severity="high",
        data={"score": 0.9},
    )

    return runtime, event


def test_intelligence_status_with_real_runtime():
    runtime, event = make_intelligence_runtime()

    runtime.process([event])

    agent = ControlServerAgent(
        intelligence_runtime=runtime,
    )
    client = TestClient(create_control_server_app(agent))

    response = client.get("/intelligence/status")

    assert response.status_code == 200

    data = response.json()

    assert data["available"] is True
    assert data["has_latest_result"] is True
    assert data["event_count"] == 1
    assert data["signal_count"] == 1
    assert data["situation_count"] == 1
    assert data["context_count"] == 1


def test_intelligence_latest_with_real_runtime():
    runtime, event = make_intelligence_runtime()

    runtime.process([event])

    agent = ControlServerAgent(
        intelligence_runtime=runtime,
    )
    client = TestClient(create_control_server_app(agent))

    response = client.get("/intelligence/latest")

    assert response.status_code == 200

    data = response.json()

    assert data["available"] is True
    assert data["has_latest_result"] is True
    assert data["result"]["events"][0]["event_id"] == "evt-api-1"
    assert data["result"]["signals"][0]["signal_id"] == "SIG-evt-api-1"


def test_status_includes_real_intelligence_state():
    runtime, event = make_intelligence_runtime()

    runtime.process([event])

    agent = ControlServerAgent(
        intelligence_runtime=runtime,
    )

    data = agent.status()

    assert data["intelligence"]["available"] is True
    assert data["intelligence"]["has_latest_result"] is True
    assert data["intelligence"]["event_count"] == 1
    assert data["intelligence"]["signal_count"] == 1


def test_agent_rejects_invalid_intelligence_runtime():
    import pytest

    with pytest.raises(TypeError):
        ControlServerAgent(
            intelligence_runtime=object(),
        )
