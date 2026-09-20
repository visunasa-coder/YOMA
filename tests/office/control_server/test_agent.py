from yoma.office.control_server import ControlServerAgent


def test_control_server_agent_starts_and_stops():
    agent = ControlServerAgent()

    assert agent.running is False

    agent.start()

    assert agent.running is True

    agent.stop()

    assert agent.running is False


def test_control_server_status_has_expected_structure():
    agent = ControlServerAgent()

    status = agent.status()

    assert status["agent"] == "yoma-control-server"
    assert status["version"] == "0.2.0"
    assert status["running"] is False
    assert "platform" in status
    assert "hostname" in status
    assert "hardware" in status


def test_control_server_discovery_returns_expected_structure():
    agent = ControlServerAgent()

    result = agent.discover()

    assert isinstance(result, dict)
    assert "platform" in result
    assert "windows_devices" in result
    assert "serial_ports" in result
    assert "network_identity" in result


def test_control_server_start_is_idempotent():
    agent = ControlServerAgent()

    agent.start()
    first_started_at = agent.status()["started_at"]

    agent.start()

    assert agent.status()["started_at"] == first_started_at

    agent.stop()

