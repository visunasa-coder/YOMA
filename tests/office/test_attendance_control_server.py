from __future__ import annotations

from fastapi.testclient import TestClient

from yoma.office.control_server.agent import ControlServerAgent
from yoma.office.control_server.api import create_control_server_app


def test_agent_attendance_environment_uses_safe_assessment():
    agent = ControlServerAgent()

    agent.discovery.discover = lambda: {
        "platform": "Windows",
        "windows_devices": [
            {
                "class": "Biometric",
                "name": "ZKTeco Attendance Device",
                "status": "OK",
                "instance_id": r"USB\VID_1234&PID_5678",
            }
        ],
        "serial_ports": [
            {
                "transport": "serial",
                "port": "COM3",
                "name": "ZKTeco Attendance Device",
                "description": "ZKTeco Biometric Device",
                "manufacturer": "ZKTeco",
                "vid": 1234,
                "pid": 5678,
            }
        ],
        "network_identity": {},
    }

    result = agent.attendance_environment()

    assert result["category"] == "attendance"
    assert result["candidate_count"] == 1
    assert result["discovery_only"] is True
    assert result["requires_human_approval"] is True
    assert result["executable"] is False
    assert result["activation_allowed"] is False

    candidate = result["candidates"][0]

    assert candidate["adapter"] == "generic_attendance"
    assert candidate["candidate"]["transport"] == "serial"


def test_agent_attendance_environment_returns_empty_when_no_device():
    agent = ControlServerAgent()

    agent.discovery.discover = lambda: {
        "platform": "Windows",
        "windows_devices": [],
        "serial_ports": [],
        "network_identity": {},
    }

    result = agent.attendance_environment()

    assert result["candidate_count"] == 0
    assert result["candidates"] == []
    assert result["discovery_only"] is True
    assert result["executable"] is False


def test_api_exposes_attendance_environment():
    agent = ControlServerAgent()

    agent.discovery.discover = lambda: {
        "platform": "Windows",
        "windows_devices": [
            {
                "class": "Biometric",
                "name": "Attendance Device",
                "status": "OK",
                "instance_id": r"USB\VID_1234&PID_5678",
            }
        ],
        "serial_ports": [],
        "network_identity": {},
    }

    app = create_control_server_app(agent)
    client = TestClient(app)

    response = client.get("/attendance/environment")

    assert response.status_code == 200

    data = response.json()

    assert data["category"] == "attendance"
    assert data["candidate_count"] == 1
    assert data["discovery_only"] is True
    assert data["requires_human_approval"] is True
    assert data["executable"] is False
    assert data["activation_allowed"] is False


def test_attendance_environment_endpoint_is_read_only():
    agent = ControlServerAgent()

    app = create_control_server_app(agent)
    client = TestClient(app)

    assert client.post("/attendance/environment").status_code == 405


def test_attendance_environment_does_not_activate_hardware():
    agent = ControlServerAgent()

    agent.discovery.discover = lambda: {
        "platform": "Windows",
        "windows_devices": [
            {
                "class": "Biometric",
                "name": "Attendance Device",
                "status": "OK",
                "instance_id": r"USB\VID_1234&PID_5678",
            }
        ],
        "serial_ports": [],
        "network_identity": {},
    }

    result = agent.attendance_environment()

    assert agent.hardware.status() == []
    assert result["activation_allowed"] is False


def test_api_contains_attendance_environment_route():
    agent = ControlServerAgent()

    app = create_control_server_app(agent)

    paths = {
        route.path
        for route in app.routes
        if hasattr(route, "path")
    }

    assert "/attendance/environment" in paths
