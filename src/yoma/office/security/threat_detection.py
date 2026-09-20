"""Defensive anomaly and threat classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThreatCategory(str, Enum):
    NONE = "none"
    AUTHENTICATION_ABUSE = "authentication_abuse"
    PRIVILEGE_ANOMALY = "privilege_anomaly"
    REQUEST_ABUSE = "request_abuse"
    UNKNOWN_DEVICE = "unknown_device"
    CONFIGURATION_TAMPERING = "configuration_tampering"
    SUSPICIOUS_FILE = "suspicious_file"
    DATA_ACCESS_ANOMALY = "data_access_anomaly"


@dataclass(frozen=True)
class ThreatAssessment:
    level: str
    category: ThreatCategory
    confidence: float
    reason: str
    recommended_action: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "category": self.category.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ThreatDetector:
    """Classifies observable security signals without executing responses."""

    def assess(
        self,
        *,
        failed_authentication_count: int = 0,
        request_rate_exceeded: bool = False,
        unknown_device: bool = False,
        privilege_anomaly: bool = False,
        configuration_tampering: bool = False,
        suspicious_file: bool = False,
        abnormal_data_access: bool = False,
    ) -> ThreatAssessment:

        if any(
            not isinstance(value, bool)
            for value in (
                request_rate_exceeded,
                unknown_device,
                privilege_anomaly,
                configuration_tampering,
                suspicious_file,
                abnormal_data_access,
            )
        ):
            raise TypeError("threat flags must be bool")

        if not isinstance(failed_authentication_count, int):
            raise TypeError("failed_authentication_count must be int")

        if failed_authentication_count < 0:
            raise ValueError("failed_authentication_count cannot be negative")

        if configuration_tampering:
            return ThreatAssessment(
                "critical",
                ThreatCategory.CONFIGURATION_TAMPERING,
                0.95,
                "configuration integrity anomaly detected",
                "restrict affected operation and require administrator review",
            )

        if privilege_anomaly:
            return ThreatAssessment(
                "critical",
                ThreatCategory.PRIVILEGE_ANOMALY,
                0.95,
                "privilege anomaly detected",
                "deny privileged operation and require administrator review",
            )

        if abnormal_data_access:
            return ThreatAssessment(
                "high",
                ThreatCategory.DATA_ACCESS_ANOMALY,
                0.90,
                "abnormal data-access pattern detected",
                "restrict data access and require review",
            )

        if suspicious_file:
            return ThreatAssessment(
                "high",
                ThreatCategory.SUSPICIOUS_FILE,
                0.90,
                "suspicious file signal detected",
                "quarantine processing path and require review",
            )

        if failed_authentication_count >= 5:
            return ThreatAssessment(
                "high",
                ThreatCategory.AUTHENTICATION_ABUSE,
                0.90,
                "repeated authentication failures detected",
                "rate-limit or temporarily restrict authentication",
            )

        if request_rate_exceeded:
            return ThreatAssessment(
                "medium",
                ThreatCategory.REQUEST_ABUSE,
                0.85,
                "request rate threshold exceeded",
                "rate-limit the requester",
            )

        if unknown_device:
            return ThreatAssessment(
                "medium",
                ThreatCategory.UNKNOWN_DEVICE,
                0.80,
                "unknown device observed",
                "require device trust review",
            )

        return ThreatAssessment(
            "none",
            ThreatCategory.NONE,
            1.0,
            "no configured threat signal detected",
            "continue normal policy evaluation",
        )
