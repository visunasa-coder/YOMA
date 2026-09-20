from __future__ import annotations

from typing import Any

from .base import AttendanceAdapter


class GenericAttendanceAdapter(AttendanceAdapter):
    """
    Generic attendance adapter.

    Supports the normalized YOMA attendance contract while
    allowing vendor-specific transport implementations later.

    Transport types:
      - http
      - tcp
      - serial
      - bluetooth
      - file
    """

    name = "generic_attendance"

    def __init__(self) -> None:
        self._connected = False
        self._device: dict[str, Any] = {}

    def capabilities(self) -> list[str]:
        return [
            "attendance_events",
            "device_probe",
            "http_transport",
            "tcp_transport",
            "serial_transport",
            "bluetooth_transport",
            "file_import",
        ]

    def discover(self) -> list[dict[str, Any]]:
        """
        Discovery is intentionally conservative.

        Actual OS/network discovery is delegated to transport
        implementations so YOMA does not blindly scan networks.
        """
        return []

    def probe(self, device: dict[str, Any]) -> bool:
        transport = device.get("transport")

        return transport in {
            "http",
            "tcp",
            "serial",
            "bluetooth",
            "file",
        }

    def connect(self, config: dict[str, Any]) -> None:
        device = config.get("device")

        if not isinstance(device, dict):
            raise ValueError("Attendance device configuration required")

        if not self.probe(device):
            raise ConnectionError(
                "Unsupported attendance device transport"
            )

        self._device = device
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._device = {}

    def health(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "device": self._device,
        }

    def fetch_events(
        self,
        *,
        employee_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:

        if not self._connected:
            raise ConnectionError(
                "Attendance adapter is not connected"
            )

        # Transport-specific implementations will populate this.
        # Returning an empty result is safer than inventing attendance.
        return []
