from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from yoma.office.adapters.base import YomaAdapter
from yoma.office.adapters.registry import AdapterRegistry
from yoma.office.operations import OperationalEvent


@dataclass(frozen=True)
class AdapterRuntimeResult:
    adapter: str
    status: str
    events_collected: int = 0
    error: str | None = None
    attempts: int = 1


class AdapterRuntimeManager:
    """
    Coordinates the lifecycle of provider-neutral YOMA adapters.

    Adapter-specific connection logic remains inside each adapter.
    This manager provides common orchestration, retry handling,
    reconnect behavior, and failure isolation.
    """

    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        *,
        max_retries: int = 2,
        retry_delay: float = 0.0,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")

        if retry_delay < 0:
            raise ValueError("retry_delay must be >= 0")

        self.registry = registry if registry is not None else AdapterRegistry()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def register(self, adapter: YomaAdapter) -> None:
        self.registry.register(adapter)

    def configure(
        self,
        adapter_name: str,
        config: dict[str, Any],
    ) -> None:
        adapter = self.registry.require(adapter_name)
        adapter.configure(config)

    def connect(
        self,
        adapter_name: str,
        config: dict[str, Any] | None = None,
    ) -> AdapterRuntimeResult:
        adapter = self.registry.require(adapter_name)

        try:
            if config is not None:
                adapter.configure(config)

            adapter.connect(config or {})

            health = adapter.health()

            if health.get("connected") is False:
                return AdapterRuntimeResult(
                    adapter=adapter.name,
                    status="unhealthy",
                    error="adapter_health_check_failed",
                )

            return AdapterRuntimeResult(
                adapter=adapter.name,
                status="connected",
            )

        except Exception as exc:
            return AdapterRuntimeResult(
                adapter=adapter.name,
                status="failed",
                error=type(exc).__name__,
            )

    def health(self, adapter_name: str) -> dict[str, Any]:
        adapter = self.registry.require(adapter_name)
        return adapter.health()

    def _collect_once(
        self,
        adapter: YomaAdapter,
    ) -> list[OperationalEvent]:
        return list(adapter.collect_events())

    def collect(
        self,
        adapter_name: str,
    ) -> tuple[list[OperationalEvent], AdapterRuntimeResult]:
        adapter = self.registry.require(adapter_name)

        attempts = 0
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            attempts += 1

            try:
                events = self._collect_once(adapter)

                return events, AdapterRuntimeResult(
                    adapter=adapter.name,
                    status="collected",
                    events_collected=len(events),
                    attempts=attempts,
                )

            except Exception as exc:
                last_error = type(exc).__name__

                if attempt >= self.max_retries:
                    break

                if self.retry_delay:
                    time.sleep(self.retry_delay)

                # Reconnect before the next attempt.
                try:
                    adapter.disconnect()
                    adapter.connect(adapter.configuration())
                except Exception as reconnect_exc:
                    last_error = type(reconnect_exc).__name__

        return [], AdapterRuntimeResult(
            adapter=adapter.name,
            status="failed",
            error=last_error,
            attempts=attempts,
        )

    def collect_all(
        self,
    ) -> tuple[list[OperationalEvent], list[AdapterRuntimeResult]]:
        events: list[OperationalEvent] = []
        results: list[AdapterRuntimeResult] = []

        for adapter in self.registry.adapters():
            adapter_events, result = self.collect(adapter.name)

            events.extend(adapter_events)
            results.append(result)

        return events, results

    def disconnect(self, adapter_name: str) -> None:
        adapter = self.registry.require(adapter_name)
        adapter.disconnect()

    def disconnect_all(self) -> None:
        for adapter in self.registry.adapters():
            try:
                adapter.disconnect()
            except Exception:
                continue

    def status(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for adapter in self.registry.adapters():
            try:
                health = adapter.health()

                results.append(
                    {
                        "name": adapter.name,
                        "category": adapter.category,
                        "configured": adapter.configured,
                        "connected": adapter.connected,
                        "health": health,
                    }
                )

            except Exception as exc:
                results.append(
                    {
                        "name": adapter.name,
                        "category": adapter.category,
                        "configured": adapter.configured,
                        "connected": adapter.connected,
                        "health": {
                            "status": "error",
                            "error": type(exc).__name__,
                        },
                    }
                )

        return results
