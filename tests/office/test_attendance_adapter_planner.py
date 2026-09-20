from yoma.office.services.attendance_adapter_planner import (
    AttendanceAdapterCandidatePlanner,
)


def test_plans_serial_attendance_adapter():
    planner = AttendanceAdapterCandidatePlanner()

    result = planner.plan(
        {
            "category": "attendance",
            "transport": "serial",
            "port": "COM3",
            "name": "ZKTeco Attendance Device",
            "manufacturer": "ZKTeco",
            "vid": 1234,
            "pid": 5678,
            "confidence": "possible",
            "source": "local_environment",
            "requires_human_approval": True,
            "executable": False,
        }
    )

    assert result["adapter"] == "generic_attendance"
    assert result["category"] == "attendance"
    assert result["candidate"]["transport"] == "serial"
    assert result["candidate"]["device"]["port"] == "COM3"
    assert result["candidate"]["device"]["vid"] == 1234
    assert result["requires_human_approval"] is True
    assert result["executable"] is False
    assert result["activation_allowed"] is False


def test_plans_windows_attendance_adapter():
    planner = AttendanceAdapterCandidatePlanner()

    result = planner.plan(
        {
            "category": "attendance",
            "transport": "windows_device",
            "name": "Biometric Attendance Device",
            "device_class": "Biometric",
            "status": "OK",
            "instance_id": r"USB\VID_1234&PID_5678",
        }
    )

    assert result["adapter"] == "generic_attendance"
    assert result["candidate"]["transport"] == "windows_device"
    assert result["candidate"]["device"]["device_class"] == "Biometric"
    assert result["candidate"]["device"]["status"] == "OK"
    assert result["requires_human_approval"] is True
    assert result["executable"] is False
    assert result["activation_allowed"] is False


def test_rejects_non_attendance_candidate():
    planner = AttendanceAdapterCandidatePlanner()

    try:
        planner.plan(
            {
                "category": "printer",
                "transport": "usb",
                "name": "Printer",
            }
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_rejects_missing_transport():
    planner = AttendanceAdapterCandidatePlanner()

    try:
        planner.plan(
            {
                "category": "attendance",
                "name": "Attendance Device",
            }
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_plan_all_is_non_executable():
    planner = AttendanceAdapterCandidatePlanner()

    results = planner.plan_all(
        [
            {
                "category": "attendance",
                "transport": "serial",
                "port": "COM3",
                "name": "Attendance Device",
            },
            {
                "category": "attendance",
                "transport": "windows_device",
                "name": "Biometric Device",
            },
        ]
    )

    assert len(results) == 2

    for result in results:
        assert result["adapter"] == "generic_attendance"
        assert result["requires_human_approval"] is True
        assert result["executable"] is False
        assert result["activation_allowed"] is False


def test_planner_does_not_call_adapter():
    planner = AttendanceAdapterCandidatePlanner()

    candidate = {
        "category": "attendance",
        "transport": "serial",
        "port": "COM3",
        "name": "ZKTeco Attendance Device",
    }

    result = planner.plan(candidate)

    assert result["activation_allowed"] is False
    assert result["executable"] is False


def test_sensitive_fields_are_not_created():
    planner = AttendanceAdapterCandidatePlanner()

    result = planner.plan(
        {
            "category": "attendance",
            "transport": "serial",
            "port": "COM3",
            "name": "Attendance Device",
            "password": "secret",
            "token": "secret-token",
        }
    )

    device = result["candidate"]["device"]

    assert "password" not in device
    assert "token" not in device
