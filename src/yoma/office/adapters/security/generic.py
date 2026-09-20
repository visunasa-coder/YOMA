from __future__ import annotations

from typing import Any

from .base import SecurityAdapter


class GenericSecurityAdapter(SecurityAdapter):
    """
    Generic security/CCTV adapter.

    Consumes authorized security events from existing
    cameras, DVRs, NVRs or security systems.

    It does not require continuous employee surveillance.
    """

    name = "generic_security"

    SUPPORTED_TRANSPORTS = {
        "onvif",
        "http",
        "tcp",
    }

    def __init__(self) -> None:
        self._connected = False
        self._device: dict[str, Any] = {}

    def capabilities(self) -> list[str]:
        return [
            "security_events",
            "device_probe",
            "device_health",
            "onvif",
            "http_transport",
            "tcp_transport",
        ]

    def discover(self) -> list[dict[str, Any]]:
        return []

    def probe(self, device: dict[str, Any]) -> bool:
        transport = device.get("transport")

        return transport in self.SUPPORTED_TRANSPORTS

    def connect(self, config: dict[str, Any]) -> None:
        device = config.get("device")

        if not isinstance(device, dict):
            raise ValueError(
                "Security device configuration required"
            )

        if not self.probe(device):
            raise ConnectionError(
                "Unsupported security device transport"
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

    def events(self, **filters: Any) -> list[dict[str, Any]]:
        if not self._connected:
            raise ConnectionError(
                "Security adapter is not connected"
            )

        return []
