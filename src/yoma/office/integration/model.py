from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntegrationStatus:
    name: str
    provider: str
    category: str
    enabled: bool
    configured: bool
    connected: bool
    health: dict[str, Any]


class Integration:
    """
    Provider-neutral description of an external YOMA integration.

    The integration layer owns lifecycle metadata.
    Provider-specific behavior remains inside YomaAdapter implementations.
    """

    def __init__(
        self,
        name: str,
        provider: str,
        category: str,
        *,
        enabled: bool = True,
    ) -> None:
        if not name:
            raise ValueError("Integration name is required")

        if not provider:
            raise ValueError("Integration provider is required")

        if not category:
            raise ValueError("Integration category is required")

        self.name = name
        self.provider = provider
        self.category = category
        self.enabled = enabled

        self._configured = False
        self._connected = False
        self._config: dict[str, Any] = {}
        self._health: dict[str, Any] = {
            "status": "unconfigured",
        }

    @property
    def configured(self) -> bool:
        return self._configured

    @property
    def connected(self) -> bool:
        return self._connected

    def configure(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise TypeError("Integration configuration must be a dictionary")

        self._config = dict(config)
        self._configured = True

        if not self._connected:
            self._health = {
                "status": "configured",
            }

    def configuration(self) -> dict[str, Any]:
        return dict(self._config)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

        if not self.enabled:
            self._connected = False
            self._health = {
                "status": "disabled",
            }

    def set_connected(
        self,
        connected: bool,
        *,
        health: dict[str, Any] | None = None,
    ) -> None:
        self._connected = bool(connected)

        if health is not None:
            self._health = dict(health)
        else:
            self._health = {
                "status": "connected" if connected else "disconnected",
            }

    def status(self) -> IntegrationStatus:
        return IntegrationStatus(
            name=self.name,
            provider=self.provider,
            category=self.category,
            enabled=self.enabled,
            configured=self.configured,
            connected=self.connected,
            health=dict(self._health),
        )
