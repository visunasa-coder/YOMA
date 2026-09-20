from yoma.office.services.attendance_environment_assessment import (
    AttendanceEnvironmentAssessment,
)


def test_assessment_detects_and_plans_serial_device():
    assessment = AttendanceEnvironmentAssessment()

    result = assessment.assess(
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
                }
            ],
            "network_identity": {},
        }
    )

    assert result["category"] == "attendance"
    assert result["candidate_count"] == 1
    assert len(result["candidates"]) == 1

    candidate = result["candidates"][0]

    assert candidate["adapter"] == "generic_attendance"
    assert candidate["candidate"]["transport"] == "serial"
    assert candidate["candidate"]["device"]["port"] == "COM3"


def test_assessment_deduplicates_discovery_sources():
    assessment = AttendanceEnvironmentAssessment()

    result = assessment.assess(
        {
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
    )

    assert result["candidate_count"] == 1
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["candidate"]["transport"] == "serial"


def test_assessment_ignores_unrelated_devices():
    assessment = AttendanceEnvironmentAssessment()

    result = assessment.assess(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "Printer",
                    "name": "Office Printer",
                    "status": "OK",
                    "instance_id": "USB\\VID_1111&PID_2222",
                }
            ],
            "serial_ports": [
                {
                    "transport": "serial",
                    "port": "COM4",
                    "name": "Arduino Controller",
                    "description": "USB Serial Device",
                    "manufacturer": "Arduino",
                }
            ],
            "network_identity": {},
        }
    )

    assert result["candidate_count"] == 0
    assert result["candidates"] == []


def test_assessment_preserves_governance():
    assessment = AttendanceEnvironmentAssessment()

    result = assessment.assess(
        {
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
    )

    assert result["discovery_only"] is True
    assert result["requires_human_approval"] is True
    assert result["executable"] is False
    assert result["activation_allowed"] is False

    candidate = result["candidates"][0]

    assert candidate["requires_human_approval"] is True
    assert candidate["executable"] is False
    assert candidate["activation_allowed"] is False


def test_assessment_does_not_expose_secrets():
    assessment = AttendanceEnvironmentAssessment()

    result = assessment.assess(
        {
            "platform": "Windows",
            "windows_devices": [
                {
                    "class": "Biometric",
                    "name": "Attendance Device",
                    "status": "OK",
                    "instance_id": r"USB\VID_1234&PID_5678",
                    "password": "secret",
                    "token": "secret-token",
                }
            ],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    text = str(result)

    assert "secret" not in text
    assert "secret-token" not in text


def test_assessment_rejects_invalid_environment():
    assessment = AttendanceEnvironmentAssessment()

    try:
        assessment.assess(None)
    except TypeError:
        pass
    else:
        raise AssertionError("Expected TypeError")


def test_assessment_can_handle_empty_environment():
    assessment = AttendanceEnvironmentAssessment()

    result = assessment.assess(
        {
            "platform": "Windows",
            "windows_devices": [],
            "serial_ports": [],
            "network_identity": {},
        }
    )

    assert result["candidate_count"] == 0
    assert result["candidates"] == []
    assert result["discovery_only"] is True
    assert result["executable"] is False
