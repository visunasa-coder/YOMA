from __future__ import annotations

import platform
import socket
from datetime import datetime, timezone
from typing import Any

from ..adapters.manager import HardwareAdapterManager
from ..intelligence.operational_unified_runtime import OperationalUnifiedRuntime
from ..services.hardware_discovery import HardwareDiscoveryService
from ..services.attendance_environment_assessment import AttendanceEnvironmentAssessment
from .classifier import HardwareClassifier


class ControlServerAgent:
    """
    YOMA Control Server Agent.

    Runs on the company's control/server computer and acts as
    the local integration point between YOMA and existing
    office hardware and optional operational intelligence.
    """

    VERSION = "0.2.0"

    def __init__(
        self,
        *,
        intelligence_runtime: OperationalUnifiedRuntime | None = None,
    ) -> None:
        if intelligence_runtime is not None and not isinstance(
            intelligence_runtime,
            OperationalUnifiedRuntime,
        ):
            raise TypeError(
                "intelligence_runtime must be an "
                "OperationalUnifiedRuntime or None"
            )

        self.discovery = HardwareDiscoveryService()
        self.attendance_assessment = AttendanceEnvironmentAssessment()
        self.classifier = HardwareClassifier()
        self.hardware = HardwareAdapterManager()
        self.intelligence_runtime = intelligence_runtime
        self._running = False
        self._started_at: datetime | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._started_at = datetime.now(timezone.utc)

    def stop(self) -> None:
        if not self._running:
            return

        for adapter in self.hardware.status():
            if adapter["connected"]:
                self.hardware.deactivate(adapter["name"])

        self._running = False
        self._started_at = None

    def discover(self) -> dict[str, Any]:
        return self.discovery.discover()

    def classified_discovery(self) -> dict[str, Any]:
        raw = self.discovery.discover()

        windows_devices = raw.get("windows_devices", [])

        classified = self.classifier.classify_all(
            windows_devices
        )

        office = [
            device
            for device in classified
            if device["yoma_category"] != "other"
        ]

        return {
            "platform": raw.get("platform"),
            "office_devices": office,
            "serial_ports": raw.get("serial_ports", []),
            "network_identity": raw.get("network_identity", {}),
        }

    def attendance_environment(self) -> dict[str, Any]:
        """
        Assess the local attendance environment safely.

        This performs discovery and adapter planning only.
        It does not probe, connect, authenticate, configure,
        activate, or modify any device.
        """
        environment = self.discovery.discover()
        return self.attendance_assessment.assess(environment)
    def intelligence_status(self) -> dict[str, Any]:
        runtime = self.intelligence_runtime

        if runtime is None:
            return {
                "available": False,
                "has_latest_result": False,
                "event_count": 0,
                "signal_count": 0,
                "situation_count": 0,
                "context_count": 0,
                "pattern_count": 0,
                "decision_count": 0,
            }

        result = runtime.last_result

        if result is None:
            return {
                "available": True,
                "has_latest_result": False,
                "event_count": 0,
                "signal_count": 0,
                "situation_count": 0,
                "context_count": 0,
                "pattern_count": 0,
                "decision_count": 0,
            }

        return {
            "available": True,
            "has_latest_result": True,
            "event_count": len(result.events),
            "signal_count": len(result.signals),
            "situation_count": len(result.situations),
            "context_count": len(result.contexts),
            "pattern_count": len(result.patterns),
            "decision_count": len(result.decisions),
        }

    def intelligence_latest(self) -> Any:
        if self.intelligence_runtime is None:
            return None

        return self.intelligence_runtime.last_result

    def status(self) -> dict[str, Any]:
        return {
            "agent": "yoma-control-server",
            "version": self.VERSION,
            "running": self._running,
            "platform": platform.system(),
            "hostname": socket.gethostname(),
            "started_at": (
                self._started_at.isoformat()
                if self._started_at
                else None
            ),
            "hardware": self.hardware.status(),
            "intelligence": self.intelligence_status(),
        }
