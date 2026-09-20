from __future__ import annotations

from dataclasses import dataclass

from yoma.office.adapters.runtime import (
    AdapterRuntimeManager,
    AdapterRuntimeResult,
)
from yoma.office.intelligence.operational_bus_runtime import (
    BusIntelligenceResult,
    OperationalBusIntelligenceRuntime,
)
from yoma.office.operations import OperationalEvent


@dataclass(frozen=True)
class ResilientIntegrationResult:
    events: tuple[OperationalEvent, ...]
    adapter_results: tuple[AdapterRuntimeResult, ...]
    intelligence_results: tuple[BusIntelligenceResult, ...]

    @property
    def successful_adapters(self) -> tuple[str, ...]:
        return tuple(
            result.adapter
            for result in self.adapter_results
            if result.status == "collected"
        )

    @property
    def failed_adapters(self) -> tuple[str, ...]:
        return tuple(
            result.adapter
            for result in self.adapter_results
            if result.status == "failed"
        )


class ResilientIntegrationIntelligenceRuntime:
    """
    Failure-isolated integration-facing intelligence runtime.

    The AdapterRuntimeManager remains responsible for:
      - adapter collection
      - retries
      - reconnects
      - adapter-level failure isolation

    This runtime is responsible only for:
      - consuming the batch collection result
      - forwarding successfully collected events to the
        existing OperationalEventBus intelligence runtime
      - preserving adapter failures in the returned result

    A failed adapter must never prevent successful adapter events
    from reaching operational intelligence.
    """

    def __init__(
        self,
        *,
        adapter_runtime: AdapterRuntimeManager,
        bus_runtime: OperationalBusIntelligenceRuntime,
    ) -> None:
        if not isinstance(adapter_runtime, AdapterRuntimeManager):
            raise TypeError(
                "adapter_runtime must be an AdapterRuntimeManager"
            )

        if not isinstance(
            bus_runtime,
            OperationalBusIntelligenceRuntime,
        ):
            raise TypeError(
                "bus_runtime must be an OperationalBusIntelligenceRuntime"
            )

        self.adapter_runtime = adapter_runtime
        self.bus_runtime = bus_runtime
        self._last_result: ResilientIntegrationResult | None = None

    @property
    def last_result(self) -> ResilientIntegrationResult | None:
        return self._last_result

    def start(self) -> None:
        self.bus_runtime.start()

    def stop(self) -> None:
        self.bus_runtime.stop()

    def close(self) -> None:
        self.bus_runtime.close()

    def collect_all(self) -> ResilientIntegrationResult:
        """
        Collect every registered adapter through the existing
        AdapterRuntimeManager.

        AdapterRuntimeManager already isolates adapter failures.
        Only successfully collected OperationalEvents are sent
        through the intelligence bus.
        """
        events, adapter_results = self.adapter_runtime.collect_all()

        event_tuple = tuple(events)
        result_tuple = tuple(adapter_results)

        intelligence_results: list[BusIntelligenceResult] = []

        for event in event_tuple:
            if not isinstance(event, OperationalEvent):
                raise TypeError(
                    "adapter collection must return OperationalEvent objects"
                )

            self.bus_runtime.event_bus.publish(event)

            intelligence_result = self.bus_runtime.last_result

            if (
                intelligence_result is None
                or intelligence_result.event != event
            ):
                raise RuntimeError(
                    "bus runtime did not process collected event"
                )

            intelligence_results.append(intelligence_result)

        result = ResilientIntegrationResult(
            events=event_tuple,
            adapter_results=result_tuple,
            intelligence_results=tuple(intelligence_results),
        )

        self._last_result = result

        return result
