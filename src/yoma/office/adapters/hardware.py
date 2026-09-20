from __future__ import annotations

from abc import abstractmethod
from typing import Any

from .base import YomaAdapter


class HardwareAdapter(YomaAdapter):
    """
    Base class for physical-office hardware integrations.

    An adapter becomes active only after a successful connection.
    """

    category = "hardware"

    def __init__(self) -> None:
        self._connected = False
        self._device_info: dict[str, Any] = {}

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    def discover(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def probe(self, device: dict[str, Any]) -> bool:
        raise NotImplementedError

    def disconnect(self) -> None:
        self._connected = False
        self._device_info = {}

    def health(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "device": self._device_info,
        }
