from __future__ import annotations

from typing import Any

from .hardware import HardwareAdapter


class HardwareAdapterManager:
    """
    Manages physical hardware adapters.

    An adapter is considered active only when:
      1. It is registered.
      2. A device is discovered.
      3. The adapter successfully probes the device.
      4. The adapter establishes a connection.
      5. Health confirms the connection.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, HardwareAdapter] = {}

    def register(self, adapter: HardwareAdapter) -> None:
        if not adapter.name:
            raise ValueError("Adapter name is required")

        if adapter.name in self._adapters:
            raise ValueError(
                f"Adapter already registered: {adapter.name}"
            )

        self._adapters[adapter.name] = adapter

    def discover_all(self) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []

        for adapter in self._adapters.values():
            for device in adapter.discover():
                devices.append(
                    {
                        "adapter": adapter.name,
                        "category": adapter.category,
                        "device": device,
                    }
                )

        return devices

    def activate(
        self,
        adapter_name: str,
        device: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        adapter = self._adapters.get(adapter_name)

        if adapter is None:
            raise ValueError(
                f"Unknown hardware adapter: {adapter_name}"
            )

        if not adapter.probe(device):
            raise ConnectionError(
                "Hardware device rejected by adapter"
            )

        adapter.connect(
            {
                "device": device,
                **(config or {}),
            }
        )

        health = adapter.health()

        if not health.get("connected"):
            adapter.disconnect()
            raise ConnectionError(
                "Hardware adapter failed health check"
            )

        return {
            "adapter": adapter.name,
            "category": adapter.category,
            "active": True,
            "health": health,
        }

    def deactivate(self, adapter_name: str) -> None:
        adapter = self._adapters.get(adapter_name)

        if adapter is None:
            raise ValueError(
                f"Unknown hardware adapter: {adapter_name}"
            )

        adapter.disconnect()

    def status(self) -> list[dict[str, Any]]:
        return [
            {
                "name": adapter.name,
                "category": adapter.category,
                "connected": adapter.connected,
                "health": adapter.health(),
            }
            for adapter in self._adapters.values()
        ]
