from __future__ import annotations

from yoma.office.intelligence.operational_bus_runtime import (
    OperationalBusIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.runtime import YomaEmbeddedRuntime


class EmbeddedOperationalIntelligence:
    """
    Bridges the existing YomaEmbeddedRuntime event bus into the
    existing M25/M26 OperationalUnifiedRuntime.

    YomaEmbeddedRuntime remains the lifecycle owner of the
    embedded operational environment. This class owns only the
    intelligence subscription bridge.
    """

    def __init__(
        self,
        *,
        embedded_runtime: YomaEmbeddedRuntime,
        intelligence_runtime: OperationalUnifiedRuntime,
    ) -> None:
        if not isinstance(embedded_runtime, YomaEmbeddedRuntime):
            raise TypeError(
                "embedded_runtime must be a YomaEmbeddedRuntime"
            )

        if not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an "
                "OperationalUnifiedRuntime"
            )

        self.embedded_runtime = embedded_runtime
        self.intelligence_runtime = intelligence_runtime

        self.bus_runtime = OperationalBusIntelligenceRuntime(
            intelligence_runtime=intelligence_runtime,
            event_bus=embedded_runtime.bus,
        )

    @property
    def running(self) -> bool:
        return self.bus_runtime.running

    @property
    def subscribed(self) -> bool:
        return self.bus_runtime.subscribed

    @property
    def last_result(self):
        return self.bus_runtime.last_result

    def start(self) -> None:
        self.bus_runtime.start()

    def stop(self) -> None:
        self.bus_runtime.stop()

    def close(self) -> None:
        self.bus_runtime.close()
