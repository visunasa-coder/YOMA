from __future__ import annotations

from typing import Any

from yoma.office.integration.model import Integration


class IntegrationRegistry:
    """
    Registry for configured YOMA integrations.

    Integrations are identified by their unique YOMA-local name.
    """

    def __init__(self) -> None:
        self._integrations: dict[str, Integration] = {}

    def register(self, integration: Integration) -> None:
        if integration.name in self._integrations:
            raise ValueError(
                f"Integration already registered: {integration.name}"
            )

        self._integrations[integration.name] = integration

    def unregister(self, name: str) -> bool:
        return self._integrations.pop(name, None) is not None

    def get(self, name: str) -> Integration | None:
        return self._integrations.get(name)

    def require(self, name: str) -> Integration:
        integration = self.get(name)

        if integration is None:
            raise KeyError(
                f"Integration not registered: {name}"
            )

        return integration

    def list(self) -> list[dict[str, Any]]:
        return [
            integration.status().__dict__.copy()
            for integration in self._integrations.values()
        ]

    def by_provider(self, provider: str) -> list[Integration]:
        return [
            integration
            for integration in self._integrations.values()
            if integration.provider == provider
        ]

    def by_category(self, category: str) -> list[Integration]:
        return [
            integration
            for integration in self._integrations.values()
            if integration.category == category
        ]

    def __len__(self) -> int:
        return len(self._integrations)
