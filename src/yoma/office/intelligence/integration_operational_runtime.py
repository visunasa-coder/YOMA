from __future__ import annotations

from dataclasses import dataclass

from yoma.office.integration.runtime import IntegrationRuntimeManager
from yoma.office.intelligence.operational_bus_runtime import (
    BusIntelligenceResult,
    OperationalBusIntelligenceRuntime,
)
from yoma.office.operations import OperationalEvent


@dataclass(frozen=True)
class IntegrationOperationalResult:
    adapter: str
    events: tuple[OperationalEvent, ...]
    adapter_result: object
    intelligence_results: tuple[BusIntelligenceResult, ...]


class IntegrationOperationalRuntime:
    """
    Integration-facing runtime coordinator.

    Composes the existing IntegrationRuntimeManager with the
    event-driven M26.2 bus intelligence runtime.

    Responsibilities are deliberately narrow:

        IntegrationRuntimeManager
            -> collect adapter events
            -> publish collected events
            -> M26.2 bus runtime processes events

    Adapter lifecycle, event contracts, intelligence, correlation,
    pattern detection, and decision logic remain owned by their
    existing components.
    """

    def __init__(
        self,
        *,
        integration_runtime: IntegrationRuntimeManager,
        bus_runtime: OperationalBusIntelligenceRuntime,
    ) -> None:
        if not isinstance(
            integration_runtime,
            IntegrationRuntimeManager,
        ):
            raise TypeError(
                "integration_runtime must be an IntegrationRuntimeManager"
            )

        if not isinstance(
            bus_runtime,
            OperationalBusIntelligenceRuntime,
        ):
            raise TypeError(
                "bus_runtime must be an OperationalBusIntelligenceRuntime"
            )

        self.integration_runtime = integration_runtime
        self.bus_runtime = bus_runtime
        self._last_result: IntegrationOperationalResult | None = None

    @property
    def last_result(self) -> IntegrationOperationalResult | None:
        return self._last_result

    def start(self) -> None:
        self.bus_runtime.start()

    def stop(self) -> None:
        self.bus_runtime.stop()

    def close(self) -> None:
        self.bus_runtime.close()

    def collect(
        self,
        adapter: str,
    ) -> IntegrationOperationalResult:
        events, adapter_result = self.integration_runtime.collect(
            adapter
        )

        intelligence_results: list[BusIntelligenceResult] = []

        for event in events:
            if not isinstance(event, OperationalEvent):
                raise TypeError(
                    "adapter collection must return OperationalEvent objects"
                )

            self.bus_runtime.event_bus.publish(event)

            result = self.bus_runtime.last_result

            if result is None or result.event != event:
                raise RuntimeError(
                    "bus runtime did not process collected event"
                )

            intelligence_results.append(result)

        result = IntegrationOperationalResult(
            adapter=adapter,
            events=tuple(events),
            adapter_result=adapter_result,
            intelligence_results=tuple(intelligence_results),
        )

        self._last_result = result
        return result

    def collect_all(
        self,
    ) -> tuple[
        list[IntegrationOperationalResult],
        list[object],
    ]:
        results: list[IntegrationOperationalResult] = []
        adapter_results: list[object] = []

        for integration in self.integration_runtime.status():
            name = integration["name"]

            result = self.collect(name)

            results.append(result)
            adapter_results.append(result.adapter_result)

        return results, adapter_results
