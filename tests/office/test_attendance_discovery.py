import pytest

from yoma.office.services.attendance_discovery import AttendanceEnvironmentDiscovery


def test_classifies_serial_attendance_candidate():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [],
            "serial_ports": [
                {
                    "transport": "serial",
                    "port": "COM3",
                    "name": "USB Serial Device",
                    "description": "ZKTeco Attendance Device",
                    "manufacturer": "ZKTeco",
                    "vid": 1234,
                    "pid": 5678,
                    "serial_number": "ABC123",
                }
            ],
            "network_identity": {
                "hostname": "TEST-PC",
                "address": "192.168.1.20",
            },
        }
    )

    assert len(result) == 1
    assert result[0]["category"] == "attendance"
    assert result[0]["transport"] == "serial"
    assert result[0]["port"] == "COM3"
    assert result[0]["requires_human_approval"] is True
    assert result[0]["executable"] is False


def test_does_not_classify_unrelated_serial_device():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [],
            "serial_ports": [
                {
                    "transport": "serial",
                    "port": "COM4",
                    "name": "Arduino Uno",
                    "description": "Arduino USB Serial",
                    "manufacturer": "Arduino",
                }
            ],
            "network_identity": {},
        }
    )

    assert result == []


def test_discovery_is_read_only():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert isinstance(result, list)

    for candidate in result:
        assert candidate["requires_human_approval"] is True
        assert candidate["executable"] is False
from yoma.office.services.attendance_discovery import AttendanceEnvironmentDiscovery


def test_classifies_windows_biometric_device():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "Biometric",
                    "name": "ZKTeco Fingerprint Attendance Device",
                    "status": "OK",
                    "instance_id": "USB\\VID_1234&PID_5678",
                }
            ],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert len(result) == 1
    assert result[0]["category"] == "attendance"
    assert result[0]["transport"] == "windows_device"
    assert result[0]["name"] == "ZKTeco Fingerprint Attendance Device"
    assert result[0]["confidence"] == "possible"
    assert result[0]["requires_human_approval"] is True
    assert result[0]["executable"] is False


def test_classifies_windows_attendance_device_by_name():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "USB",
                    "name": "Time Attendance Terminal",
                    "status": "OK",
                    "instance_id": "USB\\DEVICE123",
                }
            ],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert len(result) == 1
    assert result[0]["category"] == "attendance"
    assert result[0]["transport"] == "windows_device"


def test_ignores_unrelated_windows_device():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "AudioEndpoint",
                    "name": "USB Headset",
                    "status": "OK",
                    "instance_id": "USB\\AUDIO123",
                }
            ],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert result == []
from yoma.office.services.attendance_discovery import AttendanceEnvironmentDiscovery


def test_deduplicates_same_serial_attendance_device():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "Biometric",
                    "name": "ZKTeco Attendance Device",
                    "status": "OK",
                    "instance_id": "USB\\VID_1234&PID_5678",
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
    )

    assert len(result) == 1


def test_keeps_distinct_attendance_devices():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [],
            "serial_ports": [
                {
                    "transport": "serial",
                    "port": "COM3",
                    "name": "ZKTeco Attendance Device",
                    "description": "ZKTeco Biometric Device",
                    "manufacturer": "ZKTeco",
                    "vid": 1234,
                    "pid": 5678,
                },
                {
                    "transport": "serial",
                    "port": "COM4",
                    "name": "Fingerprint Attendance Device",
                    "description": "Biometric Attendance Terminal",
                    "manufacturer": "OtherVendor",
                    "vid": 4321,
                    "pid": 8765,
                },
            ],
            "network_identity": {},
        }
    )

    assert len(result) == 2


def test_deduplication_does_not_change_governance():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "Biometric",
                    "name": "ZKTeco Attendance Device",
                    "status": "OK",
                    "instance_id": "USB\\VID_1234&PID_5678",
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
    )

    assert len(result) == 1
    assert result[0]["requires_human_approval"] is True
    assert result[0]["executable"] is False


def test_ignores_generic_windows_system_device_with_attendance_word():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "System",
                    "name": "Direct memory access controller",
                    "description": "System device",
                    "status": "OK",
                    "instance_id": "ACPI\\PNP0200\\TEST",
                }
            ],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert result == []


def test_accepts_windows_biometric_class_without_keyword_in_name():
    discovery = AttendanceEnvironmentDiscovery()

    result = discovery.classify(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "Biometric",
                    "name": "USB Device",
                    "description": "Secure terminal",
                    "status": "OK",
                    "instance_id": "USB\\DEVICE123",
                }
            ],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert len(result) == 1
    assert result[0]["category"] == "attendance"
    assert result[0]["transport"] == "windows_device"
    assert result[0]["requires_human_approval"] is True
    assert result[0]["executable"] is False
