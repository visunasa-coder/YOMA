from __future__ import annotations

from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.intelligence.embedded_operational_intelligence import (
    EmbeddedOperationalIntelligence,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedRuntime,
)


class ControlServerIntelligenceRuntime:
    """
    Composes the existing ControlServerRuntime with the existing
    embedded operational-intelligence bridge.

    ControlServerRuntime remains the lifecycle owner for the
    Control Server and YomaEmbeddedRuntime.

    YomaEmbeddedRuntime remains the canonical OperationalEventBus owner.

    This component adds intelligence lifecycle integration without
    creating a duplicate embedded runtime, event bus, or intelligence
    runtime.

    Lifecycle operations are hardened so partial startup/shutdown
    failures do not leave the intelligence bridge orphaned.
    """

    def __init__(
        self,
        *,
        control_server_runtime: ControlServerRuntime,
        intelligence_runtime: OperationalUnifiedRuntime,
    ) -> None:
        if not isinstance(
            control_server_runtime,
            ControlServerRuntime,
        ):
            raise TypeError(
                "control_server_runtime must be a ControlServerRuntime"
            )

        if not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an OperationalUnifiedRuntime"
            )

        self.control_server_runtime = control_server_runtime

        self.bridge = EmbeddedOperationalIntelligence(
            embedded_runtime=control_server_runtime.embedded_runtime,
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

    @property
    def embedded_runtime(self):
        return self.control_server_runtime.embedded_runtime

    @property
    def agent(self):
        return self.control_server_runtime.agent

    def start(self) -> None:
        if self.running and self.control_server_runtime.running:
            return

        bridge_started = False

        try:
            if not self.bridge.running:
                self.bridge.start()
                bridge_started = True

            if not self.control_server_runtime.running:
                self.control_server_runtime.start()

        except Exception:
            if bridge_started:
                try:
                    self.bridge.stop()
                except Exception:
                    pass

            raise

    def stop(self) -> None:
        errors: list[Exception] = []

        try:
            self.control_server_runtime.stop()
        except Exception as exc:
            errors.append(exc)

        try:
            self.bridge.stop()
        except Exception as exc:
            errors.append(exc)

        if errors:
            raise errors[0]

    def close(self) -> None:
        errors: list[Exception] = []

        try:
            self.control_server_runtime.stop()
        except Exception as exc:
            errors.append(exc)

        try:
            self.bridge.close()
        except Exception as exc:
            errors.append(exc)

        if errors:
            raise errors[0]
