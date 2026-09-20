from __future__ import annotations

from dataclasses import dataclass

from yoma.office.adapters.runtime import AdapterRuntimeManager, AdapterRuntimeResult
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedResult,
    OperationalUnifiedRuntime,
)
from yoma.office.operations import OperationalEvent, OperationalEventBus


@dataclass(frozen=True)
class IntegrationIntelligenceResult:
    adapter: str
    events: tuple[OperationalEvent, ...]
    adapter_result: AdapterRuntimeResult
    intelligence: OperationalUnifiedResult


class IntegrationIntelligenceRuntime:
    """
    Connects adapter collection to the existing M25 unified
    operational intelligence runtime.

    The runtime does not duplicate adapter lifecycle management,
    event normalization, intelligence, correlation, or decision
    logic.

    Flow:

        AdapterRuntimeManager
            -> OperationalEventBus
            -> OperationalUnifiedRuntime
    """

    def __init__(
        self,
        *,
        adapter_runtime: AdapterRuntimeManager,
        intelligence_runtime: OperationalUnifiedRuntime,
        event_bus: OperationalEventBus | None = None,
    ) -> None:
        if not isinstance(adapter_runtime, AdapterRuntimeManager):
            raise TypeError(
                "adapter_runtime must be an AdapterRuntimeManager"
            )

        if not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an OperationalUnifiedRuntime"
            )

        self.adapter_runtime = adapter_runtime
        self.intelligence_runtime = intelligence_runtime
        self.event_bus = event_bus or OperationalEventBus()
        self._last_result: IntegrationIntelligenceResult | None = None

    @property
    def last_result(self) -> IntegrationIntelligenceResult | None:
        return self._last_result

    def process_events(
        self,
        adapter: str,
        events: list[OperationalEvent] | tuple[OperationalEvent, ...],
        adapter_result: AdapterRuntimeResult,
    ) -> IntegrationIntelligenceResult:
        if not isinstance(adapter_result, AdapterRuntimeResult):
            raise TypeError(
                "adapter_result must be an AdapterRuntimeResult"
            )

        event_tuple = tuple(events)

        for event in event_tuple:
            if not isinstance(event, OperationalEvent):
                raise TypeError(
                    "events must contain OperationalEvent objects"
                )

        self.event_bus.publish_many(event_tuple)

        intelligence = self.intelligence_runtime.process(
            event_tuple
        )

        result = IntegrationIntelligenceResult(
            adapter=adapter,
            events=event_tuple,
            adapter_result=adapter_result,
            intelligence=intelligence,
        )

        self._last_result = result
        return result

    def collect(
        self,
        adapter: str,
    ) -> IntegrationIntelligenceResult:
        events, adapter_result = self.adapter_runtime.collect(adapter)

        return self.process_events(
            adapter,
            events,
            adapter_result,
        )

    def collect_all(
        self,
    ) -> tuple[
        list[IntegrationIntelligenceResult],
        list[AdapterRuntimeResult],
    ]:
        results: list[IntegrationIntelligenceResult] = []
        adapter_results: list[AdapterRuntimeResult] = []

        for registered_adapter in self.adapter_runtime.registry.adapters():
            result = self.collect(registered_adapter.name)
            results.append(result)
            adapter_results.append(result.adapter_result)

        return results, adapter_results
