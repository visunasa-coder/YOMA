from __future__ import annotations

from dataclasses import dataclass

from yoma.office.adapters.scheduler import AdapterCollectionScheduler
from yoma.office.intelligence.operational_bus_runtime import (
    BusIntelligenceResult,
    OperationalBusIntelligenceRuntime,
)
from yoma.office.operations import OperationalEvent


@dataclass(frozen=True)
class ScheduledIntelligenceResult:
    events: tuple[OperationalEvent, ...]
    intelligence_results: tuple[BusIntelligenceResult, ...]


class ScheduledOperationalIntelligence:
    """
    Bridges the existing AdapterCollectionScheduler event callback
    into the existing operational intelligence bus runtime.

    The scheduler remains responsible for:
      - timing
      - collection cycles
      - adapter collection
      - adapter statistics
      - collection errors

    This bridge is responsible only for forwarding already-collected
    events into operational intelligence.
    """

    def __init__(
        self,
        *,
        scheduler: AdapterCollectionScheduler,
        bus_runtime: OperationalBusIntelligenceRuntime,
    ) -> None:
        if not isinstance(
            scheduler,
            AdapterCollectionScheduler,
        ):
            raise TypeError(
                "scheduler must be an AdapterCollectionScheduler"
            )

        if not isinstance(
            bus_runtime,
            OperationalBusIntelligenceRuntime,
        ):
            raise TypeError(
                "bus_runtime must be an OperationalBusIntelligenceRuntime"
            )

        self.scheduler = scheduler
        self.bus_runtime = bus_runtime
        self._last_result: ScheduledIntelligenceResult | None = None

    @property
    def last_result(self) -> ScheduledIntelligenceResult | None:
        return self._last_result

    def start(self) -> None:
        self.bus_runtime.start()
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop()
        self.bus_runtime.stop()

    def close(self) -> None:
        self.scheduler.stop()
        self.bus_runtime.close()

    def handle_events(
        self,
        events: list[OperationalEvent],
    ) -> ScheduledIntelligenceResult:
        event_tuple = tuple(events)

        intelligence_results: list[BusIntelligenceResult] = []

        for event in event_tuple:
            if not isinstance(event, OperationalEvent):
                raise TypeError(
                    "scheduled events must be OperationalEvent objects"
                )

            self.bus_runtime.event_bus.publish(event)

            result = self.bus_runtime.last_result

            if result is None or result.event != event:
                raise RuntimeError(
                    "bus runtime did not process scheduled event"
                )

            intelligence_results.append(result)

        result = ScheduledIntelligenceResult(
            events=event_tuple,
            intelligence_results=tuple(intelligence_results),
        )

        self._last_result = result

        return result
