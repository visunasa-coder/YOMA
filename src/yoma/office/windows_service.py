from __future__ import annotations

from typing import Any

from yoma.office.service_host import ServiceHost


class WindowsServiceAdapter:
    """Windows-facing adapter for the provider-neutral YOMA service host."""

    def __init__(self, host: ServiceHost) -> None:
        if host is None:
            raise ValueError("Service host is required")

        self.host = host

    def start(self) -> None:
        self.host.start()

    def stop(self) -> None:
        self.host.stop()

    def status(self) -> dict[str, Any]:
        return self.host.status()
