from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from yoma.office.intelligence.engine import OperationalIntelligenceEngine
from yoma.office.operations import (
    OperationalEvent,
    OperationalEventBus,
    OperationalSignal,
)


@dataclass(frozen=True)
class OperationalIntelligenceResult:
    events: tuple[OperationalEvent, ...]
    signals: tuple[OperationalSignal, ...]


class OperationalIntelligenceRuntime:
    """
    Runtime coordinator for normalized operational events.

    Composes the existing OperationalEventBus and
    OperationalIntelligenceEngine without duplicating
    intelligence rules or operational decision logic.
    """

    def __init__(
        self,
        *,
        intelligence_engine: OperationalIntelligenceEngine,
        event_bus: OperationalEventBus | None = None,
    ) -> None:
        if not isinstance(
            intelligence_engine,
            OperationalIntelligenceEngine,
        ):
            raise TypeError(
                "intelligence_engine must be an OperationalIntelligenceEngine"
            )

        self.intelligence_engine = intelligence_engine
        self._event_bus = event_bus
        self._running = False
        self._subscribed = False
        self._last_result: OperationalIntelligenceResult | None = None

        if self._event_bus is not None:
            self._event_bus.subscribe(self._handle_event)
            self._subscribed = True

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_result(self) -> OperationalIntelligenceResult | None:
        return self._last_result

    def start(self) -> None:
        if self._running:
            return

        self._running = True

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False

    def close(self) -> None:
        self.stop()

        if self._event_bus is not None and self._subscribed:
            self._event_bus.unsubscribe(self._handle_event)
            self._subscribed = False

    def process(
        self,
        events: Iterable[OperationalEvent],
    ) -> OperationalIntelligenceResult:
        normalized_events = tuple(events)

        for event in normalized_events:
            if not isinstance(event, OperationalEvent):
                raise TypeError(
                    "events must contain OperationalEvent objects"
                )

        signals = self.intelligence_engine.analyze(
            list(normalized_events)
        )

        result = OperationalIntelligenceResult(
            events=normalized_events,
            signals=tuple(signals),
        )

        self._last_result = result
        return result

    def process_event(
        self,
        event: OperationalEvent,
    ) -> OperationalIntelligenceResult:
        if not isinstance(event, OperationalEvent):
            raise TypeError("event must be an OperationalEvent")

        return self.process((event,))

    def _handle_event(self, event: OperationalEvent) -> None:
        if not self._running:
            return

        self.process_event(event)
