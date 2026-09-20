from __future__ import annotations

from dataclasses import dataclass

from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedResult,
    OperationalUnifiedRuntime,
)
from yoma.office.operations import OperationalEvent, OperationalEventBus


@dataclass(frozen=True)
class BusIntelligenceResult:
    event: OperationalEvent
    intelligence: OperationalUnifiedResult


class OperationalBusIntelligenceRuntime:
    """
    Event-driven bridge between the OperationalEventBus and the
    existing M25 OperationalUnifiedRuntime.

    The runtime owns only event-bus subscription and lifecycle.
    Intelligence, situation correlation, organization context,
    pattern detection, and decision creation remain delegated to
    OperationalUnifiedRuntime.

    Events are processed only while the runtime is running.
    """

    def __init__(
        self,
        *,
        intelligence_runtime: OperationalUnifiedRuntime,
        event_bus: OperationalEventBus,
    ) -> None:
        if not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an OperationalUnifiedRuntime"
            )

        if not isinstance(event_bus, OperationalEventBus):
            raise TypeError(
                "event_bus must be an OperationalEventBus"
            )

        self.intelligence_runtime = intelligence_runtime
        self.event_bus = event_bus
        self._running = False
        self._subscribed = False
        self._last_result: BusIntelligenceResult | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def subscribed(self) -> bool:
        return self._subscribed

    @property
    def last_result(self) -> BusIntelligenceResult | None:
        return self._last_result

    def start(self) -> None:
        if self._running:
            return

        if not self._subscribed:
            self.event_bus.subscribe(self._handle_event)
            self._subscribed = True

        self._running = True

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False

    def close(self) -> None:
        self.stop()

        if self._subscribed:
            self.event_bus.unsubscribe(self._handle_event)
            self._subscribed = False

    def process_event(
        self,
        event: OperationalEvent,
    ) -> BusIntelligenceResult:
        if not isinstance(event, OperationalEvent):
            raise TypeError(
                "event must be an OperationalEvent"
            )

        intelligence = self.intelligence_runtime.process(
            (event,)
        )

        result = BusIntelligenceResult(
            event=event,
            intelligence=intelligence,
        )

        self._last_result = result
        return result

    def _handle_event(self, event: OperationalEvent) -> None:
        if not self._running:
            return

        self.process_event(event)
