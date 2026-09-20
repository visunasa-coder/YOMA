from __future__ import annotations

from typing import Any

from yoma.office.service_host import ServiceHost


class LocalIPCServer:
    """Authenticated local command boundary for the YOMA service."""

    _ALLOWED_COMMANDS = {"health", "status", "diagnostics"}

    def __init__(self, host: ServiceHost, *, secret: str) -> None:
        if host is None:
            raise ValueError("Service host is required")

        if not secret:
            raise ValueError("IPC secret is required")

        self.host = host
        self._secret = secret
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return

        self._running = True

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False

    def request(
        self,
        command: str,
        *,
        secret: str | None = None,
    ) -> dict[str, Any]:
        if not self._running:
            raise RuntimeError("IPC server is not running")

        if secret != self._secret:
            raise PermissionError("Invalid IPC authentication")

        if command not in self._ALLOWED_COMMANDS:
            raise ValueError(f"Unsupported IPC command: {command}")

        if command == "health":
            return self.host.health()

        if command == "status":
            return self.host.status()

        return {
            "service": "yoma",
            "service_state": self.host.status()["state"],
            "runtime_state": self.host.status()["runtime_state"],
            "runtime_running": self.host.status()["runtime_running"],
            "ipc_running": self.running,
        }
