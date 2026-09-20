"""Unified defensive security runtime for YOMA."""

from __future__ import annotations

from typing import Any

from .audit import SecurityAuditChain
from .core import SecurityAssessment, SecurityCore
from .data_guard import DatabaseGuard, FileGuard
from .rbac import RBAC, SecurityIdentity, SecurityRole
from .request_guard import RateLimiter, RequestGuard
from .threat_detection import ThreatAssessment, ThreatDetector


class SecurityRuntime:
    """
    Composes YOMA security layers.

    This runtime evaluates security state only. It does not execute
    commands, activate integrations, modify databases, or authorize
    itself.
    """

    def __init__(self) -> None:
        self.core = SecurityCore()
        self.rbac = RBAC()
        self.request_guard = RequestGuard()
        self.rate_limiter = RateLimiter()
        self.threat_detector = ThreatDetector()
        self.file_guard = FileGuard()
        self.database_guard = DatabaseGuard()
        self.audit = SecurityAuditChain()

    def assess(
        self,
        *,
        authenticated: bool,
        authorized: bool,
        trust_level: str = "unknown",
        threat_level: str = "none",
        approval_present: bool = False,
        request_valid: bool = True,
    ) -> SecurityAssessment:
        result = self.core.assess(
            authenticated=authenticated,
            authorized=authorized,
            trust_level=trust_level,
            threat_level=threat_level,
            approval_present=approval_present,
            request_valid=request_valid,
        )

        self.audit.record(
            event_type="security_assessment",
            actor="yoma-security-runtime",
            resource="security",
            status=result.decision.value,
            metadata={
                "threat_level": result.threat_level.value,
                "trust_level": result.trust_level.value,
                "reason": result.reason,
            },
        )

        return result

    def threat_assess(self, **signals: Any) -> ThreatAssessment:
        result = self.threat_detector.assess(**signals)

        self.audit.record(
            event_type="threat_assessment",
            actor="yoma-security-runtime",
            resource="security",
            status=result.level,
            metadata={
                "category": result.category.value,
                "confidence": result.confidence,
            },
        )

        return result

    def status(self) -> dict[str, Any]:
        return {
            "security": "active",
            "fail_closed": True,
            "authentication_required": True,
            "authorization_required": True,
            "threat_detection": True,
            "request_guard": True,
            "rate_limiting": True,
            "file_guard": True,
            "database_guard": True,
            "audit_chain": True,
            "audit_chain_valid": self.audit.verify(),
            "requires_human_approval": True,
            "executable": False,
        }


__all__ = [
    "SecurityRuntime",
    "SecurityCore",
    "SecurityAssessment",
    "SecurityRole",
    "SecurityIdentity",
    "RBAC",
    "ThreatDetector",
    "ThreatAssessment",
    "RequestGuard",
    "RateLimiter",
    "FileGuard",
    "DatabaseGuard",
    "SecurityAuditChain",
]
