from fastapi.testclient import TestClient

from yoma.office.control_server import (
    ControlServerAgent,
    create_control_server_app,
)


def test_classified_discovery_endpoint():
    agent = ControlServerAgent()
    client = TestClient(create_control_server_app(agent))

    response = client.get("/discovery/classified")

    assert response.status_code == 200

    data = response.json()

    assert "platform" in data
    assert "office_devices" in data
    assert "serial_ports" in data
    assert "network_identity" in data

    assert isinstance(data["office_devices"], list)

    for device in data["office_devices"]:
        assert device["yoma_category"] != "other"
