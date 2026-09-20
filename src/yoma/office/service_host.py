from __future__ import annotations

from typing import Any

from yoma.office.runtime import YomaEmbeddedRuntime


class ServiceHost:
    """Provider-neutral host for the YOMA embedded runtime."""

    def __init__(self, runtime: YomaEmbeddedRuntime) -> None:
        if runtime is None:
            raise ValueError("Runtime is required")

        self.runtime = runtime
        self._state = "stopped"

    @property
    def running(self) -> bool:
        return self._state == "running"

    def start(self) -> None:
        if self.running:
            return

        try:
            self._state = "starting"
            self.runtime.start()
            self._state = "running"
        except Exception:
            self._state = "failed"
            raise

    def stop(self) -> None:
        if self._state == "stopped":
            return

        try:
            self._state = "stopping"
            self.runtime.stop()
        finally:
            self._state = "stopped"

    def status(self) -> dict[str, Any]:
        runtime_status = self.runtime.status()

        return {
            "state": self._state,
            "runtime_state": runtime_status.runtime_state,
            "runtime_running": runtime_status.running,
        }

    def health(self) -> dict[str, Any]:
        runtime_status = self.runtime.status()
        healthy = (
            self._state == "running"
            and runtime_status.running
            and runtime_status.runtime_state == "running"
        )

        return {
            "service": "yoma",
            "healthy": healthy,
            "service_state": self._state,
            "runtime_state": runtime_status.runtime_state,
            "runtime_running": runtime_status.running,
        }
