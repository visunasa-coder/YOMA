"""Unified M48 host security runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .adaptive_defense import AdaptiveAttackDefense, SecuritySignal
from .configuration_integrity import ConfigurationIntegrity
from .containment import EmergencyContainment
from .filesystem_monitor import FileSystemMonitor
from .host_access import HostAccessBoundary
from .host_policy import HostSecurityPolicy
from .integrity import IntegrityVerifier
from .process_monitor import ProcessMonitor
from .secret_boundary import SecretBoundary


@dataclass(frozen=True)
class HostSecurityIncident:
    timestamp: str
    category: str
    severity: str
    source_id: str
    reason: str
    containment_required: bool = False
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "category": self.category,
            "severity": self.severity,
            "source_id": self.source_id,
            "reason": self.reason,
            "containment_required": self.containment_required,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class HostSecurityRuntime:
    """M48 defensive host-security composition layer."""

    def __init__(self) -> None:
        self.policy = HostSecurityPolicy()
        self.host_access = HostAccessBoundary()
        self.secret_boundary = SecretBoundary()
        self.integrity = IntegrityVerifier()
        self.process_monitor = ProcessMonitor()
        self.configuration_integrity = ConfigurationIntegrity()
        self.filesystem_monitor = FileSystemMonitor()
        self.adaptive_defense = AdaptiveAttackDefense()
        self.containment = EmergencyContainment()
        self._incidents: list[HostSecurityIncident] = []

    def observe_attack(
        self,
        *,
        source_id: str,
        signal: str,
        severity: str = "medium",
    ):
        reputation = self.adaptive_defense.observe(
            SecuritySignal(
                source_id=source_id,
                signal=signal,
                severity=severity,
            )
        )

        if reputation.state.value == "blocked":
            self.containment.enter_restricted(
                f"source {source_id} triggered host security block"
            )

            self._incidents.append(
                HostSecurityIncident(
                    datetime.now(timezone.utc).isoformat(),
                    "adaptive_attack_defense",
                    "high" if severity != "critical" else "critical",
                    source_id,
                    reputation.reason,
                    containment_required=True,
                )
            )

        return reputation

    def incidents(self) -> list[HostSecurityIncident]:
        return list(self._incidents)

    def status(self) -> dict[str, Any]:
        return {
            "host_security": "active",
            "policy": self.policy.as_dict(),
            "adaptive_blocking": True,
            "temporary_blocking": True,
            "host_containment_state": self.containment.state.value,
            "incident_count": len(self._incidents),
            "sensitive_execution_allowed": False,
            "requires_human_approval": True,
            "executable": False,
        }
