from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from yoma.office.operations import OperationalEvent


class YomaAdapter(ABC):
    """
    Provider-neutral adapter contract.

    YOMA owns the internal API and intelligence layer.
    Adapters translate external systems into YOMA-compatible operations.
    """

    name: str
    category: str

    def __init__(self) -> None:
        self._configured = False
        self._connected = False
        self._config: dict[str, Any] = {}

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate adapter configuration without connecting."""
        if not isinstance(config, dict):
            raise TypeError("Adapter configuration must be a dictionary")

    def configure(self, config: dict[str, Any]) -> None:
        """Store validated adapter configuration."""
        self.validate_config(config)
        self._config = dict(config)
        self._configured = True

    def configuration(self) -> dict[str, Any]:
        """
        Return a defensive copy of the adapter configuration.

        This is intended for internal lifecycle operations such as
        reconnect. Secrets must still never be exposed through metadata
        or health responses.
        """
        return dict(self._config)

    @property
    def configured(self) -> bool:
        return self._configured

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def connect(self, config: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    def collect_events(self) -> Iterable[OperationalEvent]:
        return ()

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities()

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "capabilities": self.capabilities(),
            "configured": self.configured,
            "connected": self.connected,
        }
