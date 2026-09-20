from __future__ import annotations

from typing import Any

from .base import YomaAdapter


class AdapterRegistry:
    """Central registry for provider-neutral YOMA adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, YomaAdapter] = {}

    def register(self, adapter: YomaAdapter) -> None:
        if not adapter.name:
            raise ValueError("Adapter name is required")

        if adapter.name in self._adapters:
            raise ValueError(f"Adapter already registered: {adapter.name}")

        self._adapters[adapter.name] = adapter

    def unregister(self, name: str) -> bool:
        return self._adapters.pop(name, None) is not None

    def get(self, name: str) -> YomaAdapter | None:
        return self._adapters.get(name)

    def require(self, name: str) -> YomaAdapter:
        adapter = self.get(name)
        if adapter is None:
            raise KeyError(f"Adapter not registered: {name}")
        return adapter

    def list(self) -> list[dict[str, Any]]:
        return [adapter.metadata() for adapter in self._adapters.values()]

    def adapters(self) -> list[YomaAdapter]:
        """Return the registered adapter instances."""
        return list(self._adapters.values())

    def by_category(self, category: str) -> list[YomaAdapter]:
        return [
            adapter
            for adapter in self._adapters.values()
            if adapter.category == category
        ]

    def capability(self, capability: str) -> list[YomaAdapter]:
        return [
            adapter
            for adapter in self._adapters.values()
            if adapter.supports(capability)
        ]

    def collect_events(self) -> list:
        events = []

        for adapter in self._adapters.values():
            events.extend(adapter.collect_events())

        return events

    def __len__(self) -> int:
        return len(self._adapters)
