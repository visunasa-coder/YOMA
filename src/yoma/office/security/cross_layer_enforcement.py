from __future__ import annotations

from dataclasses import dataclass

from .unified_policy import (
    SecurityEnforcementDecision,
    UnifiedSecurityDecision,
    UnifiedSecurityPolicyPlane,
)


@dataclass(frozen=True)
class SecurityLayerState:
    request_valid: bool
    identity_allowed: bool
    host_safe: bool
    threat_safe: bool
    data_allowed: bool
    governance_allowed: bool
    approval_present: bool = False
    review_required: bool = False


class CrossLayerSecurityEnforcer:
    def __init__(self, policy: UnifiedSecurityPolicyPlane | None = None):
        self.policy = policy or UnifiedSecurityPolicyPlane()

    def enforce(self, state: SecurityLayerState) -> UnifiedSecurityDecision:
        return self.policy.evaluate(
            request_valid=state.request_valid,
            identity_allowed=state.identity_allowed,
            host_safe=state.host_safe,
            threat_safe=state.threat_safe,
            data_allowed=state.data_allowed,
            governance_allowed=state.governance_allowed,
            approval_present=state.approval_present,
            review_required=state.review_required,
        )
