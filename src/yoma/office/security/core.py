"""YOMA defensive security core."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SecurityDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustLevel(str, Enum):
    UNKNOWN = "unknown"
    UNTRUSTED = "untrusted"
    LIMITED = "limited"
    TRUSTED = "trusted"


@dataclass(frozen=True)
class SecurityAssessment:
    decision: SecurityDecision
    threat_level: ThreatLevel
    trust_level: TrustLevel
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "threat_level": self.threat_level.value,
            "trust_level": self.trust_level.value,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class SecurityCore:
    """Fail-closed defensive security evaluator."""

    def assess(
        self,
        *,
        authenticated: bool,
        authorized: bool,
        trust_level: TrustLevel | str = TrustLevel.UNKNOWN,
        threat_level: ThreatLevel | str = ThreatLevel.NONE,
        approval_present: bool = False,
        request_valid: bool = True,
    ) -> SecurityAssessment:

        if not isinstance(authenticated, bool):
            raise TypeError("authenticated must be bool")
        if not isinstance(authorized, bool):
            raise TypeError("authorized must be bool")
        if not isinstance(approval_present, bool):
            raise TypeError("approval_present must be bool")
        if not isinstance(request_valid, bool):
            raise TypeError("request_valid must be bool")

        try:
            trust = (
                trust_level
                if isinstance(trust_level, TrustLevel)
                else TrustLevel(trust_level)
            )
        except ValueError as exc:
            raise ValueError("invalid trust_level") from exc

        try:
            threat = (
                threat_level
                if isinstance(threat_level, ThreatLevel)
                else ThreatLevel(threat_level)
            )
        except ValueError as exc:
            raise ValueError("invalid threat_level") from exc

        if not request_valid:
            return SecurityAssessment(
                SecurityDecision.DENY,
                threat,
                trust,
                "request validation failed",
            )

        if threat in {ThreatLevel.HIGH, ThreatLevel.CRITICAL}:
            return SecurityAssessment(
                SecurityDecision.DENY,
                threat,
                trust,
                "high-risk threat state",
            )

        if not authenticated:
            return SecurityAssessment(
                SecurityDecision.DENY,
                threat,
                trust,
                "authentication required",
            )

        if not authorized:
            return SecurityAssessment(
                SecurityDecision.DENY,
                threat,
                trust,
                "authorization required",
            )

        if trust in {TrustLevel.UNKNOWN, TrustLevel.UNTRUSTED}:
            return SecurityAssessment(
                SecurityDecision.REVIEW,
                threat,
                trust,
                "trusted identity or device required",
            )

        if threat == ThreatLevel.MEDIUM:
            return SecurityAssessment(
                SecurityDecision.REVIEW,
                threat,
                trust,
                "medium-risk request requires review",
            )

        if not approval_present:
            return SecurityAssessment(
                SecurityDecision.REVIEW,
                threat,
                trust,
                "governed approval required",
            )

        return SecurityAssessment(
            SecurityDecision.ALLOW,
            threat,
            trust,
            "security conditions satisfied; existing governed authorization required for execution",
        )
