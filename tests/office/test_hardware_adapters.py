from yoma.office.adapters.manager import HardwareAdapterManager
from yoma.office.adapters.attendance.generic import (
    GenericAttendanceAdapter,
)
from yoma.office.adapters.security.generic import (
    GenericSecurityAdapter,
)


def test_attendance_adapter_accepts_supported_transport():

    adapter = GenericAttendanceAdapter()

    assert adapter.probe(
        {"transport": "tcp"}
    )

    assert adapter.probe(
        {"transport": "serial"}
    )

    assert adapter.probe(
        {"transport": "bluetooth"}
    )


def test_attendance_adapter_rejects_unknown_transport():

    adapter = GenericAttendanceAdapter()

    assert not adapter.probe(
        {"transport": "unknown"}
    )


def test_security_adapter_accepts_onvif():

    adapter = GenericSecurityAdapter()

    assert adapter.probe(
        {"transport": "onvif"}
    )


def test_security_adapter_rejects_unknown_transport():

    adapter = GenericSecurityAdapter()

    assert not adapter.probe(
        {"transport": "unknown"}
    )


def test_hardware_activation_requires_adapter():

    manager = HardwareAdapterManager()

    adapter = GenericAttendanceAdapter()
    manager.register(adapter)

    result = manager.activate(
        "generic_attendance",
        {
            "transport": "tcp",
            "host": "192.168.1.100",
        },
    )

    assert result["active"] is True
    assert result["health"]["connected"] is True


def test_unknown_adapter_cannot_activate():

    manager = HardwareAdapterManager()

    try:
        manager.activate(
            "does_not_exist",
            {"transport": "tcp"},
        )
    except ValueError:
        return

    raise AssertionError(
        "Unknown adapter was incorrectly activated"
    )


def test_disconnected_adapter_cannot_fetch_attendance():

    adapter = GenericAttendanceAdapter()

    try:
        adapter.fetch_events()
    except ConnectionError:
        return

    raise AssertionError(
        "Disconnected attendance adapter returned data"
    )


def test_disconnected_security_adapter_cannot_return_events():

    adapter = GenericSecurityAdapter()

    try:
        adapter.events()
    except ConnectionError:
        return

    raise AssertionError(
        "Disconnected security adapter returned events"
    )
