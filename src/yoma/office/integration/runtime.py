from __future__ import annotations

from pathlib import Path
from typing import Any

from yoma.office.adapters import AdapterRuntimeManager, YomaAdapter
from yoma.office.integration.model import Integration
from yoma.office.integration.persistence import IntegrationPersistence
from yoma.office.integration.registry import IntegrationRegistry


class IntegrationRuntimeManager:
    """
    Coordinates integration metadata, persistence, and adapter runtime.

    Integration owns provider-neutral lifecycle state.
    IntegrationPersistence owns durable configuration.
    AdapterRuntimeManager owns adapter-specific execution.

    Persisted integrations are restored as disconnected.
    Connection is always an explicit runtime action.
    """

    def __init__(
        self,
        registry: IntegrationRegistry | None = None,
        adapter_runtime: AdapterRuntimeManager | None = None,
        persistence: IntegrationPersistence | None = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else IntegrationRegistry()
        )

        self.adapter_runtime = (
            adapter_runtime
            if adapter_runtime is not None
            else AdapterRuntimeManager()
        )

        self.persistence = persistence

        self._adapters: dict[str, YomaAdapter] = {}

    def register(
        self,
        integration: Integration,
        adapter: YomaAdapter,
    ) -> None:
        if integration.name != adapter.name:
            raise ValueError(
                "Integration name must match adapter name"
            )

        self.registry.register(integration)
        self.adapter_runtime.register(adapter)
        self._adapters[integration.name] = adapter

        self._persist(integration)

    def get(self, name: str) -> Integration:
        return self.registry.require(name)

    def configure(
        self,
        name: str,
        config: dict[str, Any],
    ) -> None:
        integration = self.registry.require(name)
        adapter = self._adapters[name]

        integration.configure(config)
        adapter.configure(config)

        self._persist(integration)

    def enable(self, name: str) -> None:
        integration = self.registry.require(name)
        integration.set_enabled(True)

        self._persist(integration)

    def disable(self, name: str) -> None:
        integration = self.registry.require(name)

        if integration.connected:
            try:
                self.adapter_runtime.disconnect(name)
            finally:
                integration.set_connected(False)

        integration.set_enabled(False)

        self._persist(integration)

    def connect(self, name: str):
        integration = self.registry.require(name)

        if not integration.enabled:
            raise RuntimeError(
                f"Integration is disabled: {name}"
            )

        if not integration.configured:
            raise RuntimeError(
                f"Integration is not configured: {name}"
            )

        result = self.adapter_runtime.connect(
            name,
            integration.configuration(),
        )

        if result.status == "connected":
            integration.set_connected(
                True,
                health={"status": "connected"},
            )
        elif result.status == "unhealthy":
            integration.set_connected(
                False,
                health={
                    "status": "unhealthy",
                    "error": result.error,
                },
            )
        else:
            integration.set_connected(
                False,
                health={
                    "status": "failed",
                    "error": result.error,
                },
            )

        self._persist(integration)

        return result

    def disconnect(self, name: str) -> None:
        integration = self.registry.require(name)

        try:
            self.adapter_runtime.disconnect(name)
        finally:
            integration.set_connected(False)
            self._persist(integration)

    def health(self, name: str) -> dict[str, Any]:
        integration = self.registry.require(name)

        try:
            health = self.adapter_runtime.health(name)
            integration.set_connected(
                integration.connected,
                health=health,
            )
            self._persist(integration)
            return health
        except Exception as exc:
            health = {
                "status": "error",
                "error": type(exc).__name__,
            }

            integration.set_connected(False, health=health)
            self._persist(integration)

            return health

    def collect(self, name: str):
        integration = self.registry.require(name)

        if not integration.enabled:
            raise RuntimeError(
                f"Integration is disabled: {name}"
            )

        if not integration.connected:
            raise RuntimeError(
                f"Integration is not connected: {name}"
            )

        return self.adapter_runtime.collect(name)

    def status(self) -> list[dict[str, Any]]:
        return self.registry.list()

    def restore(self) -> list[Integration]:
        """
        Restore persisted integrations into the registry.

        Adapters must still be registered separately because adapter
        implementations are runtime objects. Restored integrations
        remain disconnected and are never auto-connected.
        """
        if self.persistence is None:
            return []

        restored: list[Integration] = []

        for record in self.persistence.load_all():
            if self.registry.get(record["name"]) is not None:
                continue

            integration = Integration(
                record["name"],
                record["provider"],
                record["category"],
                enabled=record["enabled"],
            )

            if record["configured"]:
                integration.configure(record["configuration"])

            # Persisted connections are intentionally not restored as
            # active connections. A restart must require explicit connect().
            integration.set_connected(False)

            self.registry.register(integration)
            restored.append(integration)

        return restored

    def unregister(self, name: str) -> bool:
        integration = self.registry.get(name)

        if integration is None:
            return False

        if integration.connected:
            try:
                self.adapter_runtime.disconnect(name)
            except Exception:
                pass

        self._adapters.pop(name, None)
        self.adapter_runtime.registry.unregister(name)

        result = self.registry.unregister(name)

        if result and self.persistence is not None:
            self.persistence.delete(name)

        return result

    def _persist(self, integration: Integration) -> None:
        if self.persistence is not None:
            self.persistence.save(integration)
