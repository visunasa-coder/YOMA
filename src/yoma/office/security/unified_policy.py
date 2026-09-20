from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SecurityEnforcementDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


@dataclass(frozen=True)
class UnifiedSecurityDecision:
    decision: SecurityEnforcementDecision
    reason: str
    source_layers: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "source_layers": list(self.source_layers),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class UnifiedSecurityPolicyPlane:
    """
    Normalizes security decisions from M47-M51.

    This component has no execution capability.
    """

    def evaluate(
        self,
        *,
        request_valid: bool,
        identity_allowed: bool,
        host_safe: bool,
        threat_safe: bool,
        data_allowed: bool,
        governance_allowed: bool,
        approval_present: bool = False,
        review_required: bool = False,
    ) -> UnifiedSecurityDecision:

        if not request_valid:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.DENY,
                "invalid_request",
                ("m47_request_security",),
            )

        if not host_safe:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.DENY,
                "host_security_failure",
                ("m48_host_security",),
            )

        if not identity_allowed:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.DENY,
                "identity_or_access_denied",
                ("m51_identity",),
            )

        if not threat_safe:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.DENY,
                "threat_detected",
                ("m47_threat_detection", "m49_incident_operations"),
            )

        if not data_allowed:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.DENY,
                "data_policy_denied",
                ("m50_data_protection",),
            )

        if not governance_allowed:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.DENY,
                "governance_denied",
                ("governance",),
            )

        if review_required and not approval_present:
            return UnifiedSecurityDecision(
                SecurityEnforcementDecision.REVIEW,
                "human_approval_required",
                ("governance", "m52_enforcement"),
            )

        return UnifiedSecurityDecision(
            SecurityEnforcementDecision.ALLOW,
            "security_policy_satisfied",
            (
                "m47_request_security",
                "m48_host_security",
                "m50_data_protection",
                "m51_identity",
                "governance",
            ),
        )
