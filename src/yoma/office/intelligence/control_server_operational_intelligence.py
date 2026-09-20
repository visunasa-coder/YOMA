from __future__ import annotations

from yoma.office.control_server.agent import ControlServerAgent
from yoma.office.intelligence.embedded_operational_intelligence import (
    EmbeddedOperationalIntelligence,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)
from yoma.office.runtime import YomaEmbeddedRuntime


class ControlServerOperationalIntelligence:
    """
    Bridges the Control Server lifecycle to the existing embedded
    operational-intelligence runtime.

    ControlServerRuntime owns the YomaEmbeddedRuntime.
    YomaEmbeddedRuntime owns the canonical OperationalEventBus.
    This component only composes the existing objects.
    """

    def __init__(
        self,
        *,
        agent: ControlServerAgent,
        embedded_runtime: YomaEmbeddedRuntime,
        intelligence_runtime: OperationalUnifiedRuntime,
    ) -> None:
        if not isinstance(agent, ControlServerAgent):
            raise TypeError(
                "agent must be a ControlServerAgent"
            )

        if not isinstance(
            embedded_runtime,
            YomaEmbeddedRuntime,
        ):
            raise TypeError(
                "embedded_runtime must be a YomaEmbeddedRuntime"
            )

        if not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an OperationalUnifiedRuntime"
            )

        self.agent = agent
        self.embedded_runtime = embedded_runtime

        self.bridge = EmbeddedOperationalIntelligence(
            embedded_runtime=embedded_runtime,
            intelligence_runtime=intelligence_runtime,
        )

    @property
    def running(self) -> bool:
        return self.bridge.running

    @property
    def subscribed(self) -> bool:
        return self.bridge.subscribed

    @property
    def last_result(self):
        return self.bridge.last_result

    def start(self) -> None:
        self.bridge.start()

    def stop(self) -> None:
        self.bridge.stop()

    def close(self) -> None:
        self.bridge.close()
