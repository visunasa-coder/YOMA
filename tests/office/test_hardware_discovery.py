from yoma.office.services.hardware_discovery import (
    HardwareDiscoveryService,
)


def test_hardware_discovery_returns_expected_structure():

    result = HardwareDiscoveryService().discover()

    assert isinstance(result, dict)

    assert "platform" in result
    assert "windows_devices" in result
    assert "serial_ports" in result
    assert "network_identity" in result


def test_serial_discovery_returns_list():

    result = HardwareDiscoveryService().discover_serial_ports()

    assert isinstance(result, list)

    for device in result:
        assert device["transport"] == "serial"
        assert "port" in device


def test_network_identity_has_expected_fields():

    result = HardwareDiscoveryService().local_network_identity()

    assert "hostname" in result
    assert "address" in result


def test_windows_discovery_returns_list():

    result = HardwareDiscoveryService().discover_windows_devices()

    assert isinstance(result, list)

    for device in result:
        assert "name" in device
        assert "status" in device
