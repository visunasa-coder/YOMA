from __future__ import annotations

from typing import Any

from yoma.office.intelligence.control_server_intelligence_runtime import (
    ControlServerIntelligenceRuntime,
)


class ControlServerIntelligenceStatus:
    """
    Read-only observability surface for the Control Server intelligence
    runtime.

    This component does not own lifecycle, create buses, execute actions,
    or mutate intelligence state. It only exposes a safe status snapshot
    from the existing M27.4 runtime.
    """

    def __init__(
        self,
        *,
        runtime: ControlServerIntelligenceRuntime,
    ) -> None:
        if not isinstance(
            runtime,
            ControlServerIntelligenceRuntime,
        ):
            raise TypeError(
                "runtime must be a ControlServerIntelligenceRuntime"
            )

        self.runtime = runtime

    def snapshot(self) -> dict[str, Any]:
        result = self.runtime.last_result

        if result is None:
            counts = {
                "event_count": 0,
                "signal_count": 0,
                "situation_count": 0,
                "context_count": 0,
                "pattern_count": 0,
                "decision_count": 0,
            }
        else:
            unified = result.intelligence

            counts = {
                "event_count": len(unified.events),
                "signal_count": len(unified.signals),
                "situation_count": len(unified.situations),
                "context_count": len(unified.contexts),
                "pattern_count": len(unified.patterns),
                "decision_count": len(unified.decisions),
            }

        return {
            "available": True,
            "running": self.runtime.running,
            "subscribed": self.runtime.subscribed,
            "has_latest_result": result is not None,
            **counts,
        }

    def latest_summary(self) -> dict[str, Any]:
        result = self.runtime.last_result

        if result is None:
            return {
                "available": True,
                "has_latest_result": False,
                "event_id": None,
                "event_type": None,
                "signal_count": 0,
                "situation_count": 0,
                "context_count": 0,
                "pattern_count": 0,
                "decision_count": 0,
            }

        unified = result.intelligence

        return {
            "available": True,
            "has_latest_result": True,
            "event_id": result.event.event_id,
            "event_type": result.event.event_type,
            "signal_count": len(unified.signals),
            "situation_count": len(unified.situations),
            "context_count": len(unified.contexts),
            "pattern_count": len(unified.patterns),
            "decision_count": len(unified.decisions),
        }
