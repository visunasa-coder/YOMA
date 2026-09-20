from __future__ import annotations

from dataclasses import dataclass

from .cross_layer_enforcement import (
    CrossLayerSecurityEnforcer,
    SecurityLayerState,
)
from .enforcement_boundary import FinalSecurityEnforcementBoundary
from .fail_safe import SecurityFailSafe
from .integration_security import EnterpriseIntegrationSecurity
from .security_context import SecurityContext
from .security_state import SecurityStatePropagator
from .unified_policy import UnifiedSecurityDecision


@dataclass(frozen=True)
class UnifiedSecurityRuntimeResult:
    decision: UnifiedSecurityDecision
    boundary_decision: str
    execution_authorized: bool
    requires_human_approval: bool
    executable: bool
    restricted: bool
    fail_safe_state: str
    context_valid: bool


class UnifiedSecurityRuntime:
    """
    M52 composition layer.

    M52 can evaluate and enforce security policy, but it
    cannot execute business actions.
    """

    def __init__(self):
        self.enforcer = CrossLayerSecurityEnforcer()
        self.boundary = FinalSecurityEnforcementBoundary()
        self.state = SecurityStatePropagator()
        self.integrations = EnterpriseIntegrationSecurity()
        self.fail_safe = SecurityFailSafe()

    def evaluate(
        self,
        *,
        actor_id: str,
        request_id: str,
        source_id: str,
        identity_allowed: bool = True,
        device_trusted: bool = True,
        session_valid: bool = True,
        host_safe: bool = True,
        threat_safe: bool = True,
        data_allowed: bool = True,
        governance_allowed: bool = True,
        review_required: bool = True,
        approval_present: bool = False,
        host_state: str = "healthy",
        incident_severity: str = "info",
        data_state: str = "allowed",
        governed_authorization: bool = False,
    ) -> UnifiedSecurityRuntimeResult:

        context = SecurityContext(
            actor_id=actor_id,
            identity_trusted=identity_allowed,
            device_trusted=device_trusted,
            session_valid=session_valid,
            request_id=request_id,
            source_id=source_id,
            host_state=host_state,
            threat_level="none" if threat_safe else "high",
        )

        state = self.state.derive(
            host_state=host_state,
            incident_severity=incident_severity,
            data_state=data_state,
        )

        decision = self.enforcer.enforce(
            SecurityLayerState(
                request_valid=bool(actor_id and request_id and source_id),
                identity_allowed=identity_allowed and device_trusted and session_valid,
                host_safe=host_safe and not state.host_restricted,
                threat_safe=threat_safe and not state.incident_restricted,
                data_allowed=data_allowed and not state.data_restricted,
                governance_allowed=governance_allowed,
                approval_present=approval_present,
                review_required=review_required,
            )
        )

        boundary = self.boundary.evaluate(
            decision,
            governed_authorization=governed_authorization,
        )

        safe = decision.decision.value != "deny"

        fail_safe = self.fail_safe.evaluate(
            security_valid=safe,
            evidence_preserved=not state.incident_restricted,
            recovery_approved=False,
        )

        return UnifiedSecurityRuntimeResult(
            decision=decision,
            boundary_decision=boundary.decision,
            execution_authorized=False,
            requires_human_approval=True,
            executable=False,
            restricted=state.restricted,
            fail_safe_state=fail_safe.value,
            context_valid=context.can_continue(),
        )

    def status(self) -> dict:
        return {
            "m52_active": True,
            "unified_policy_plane": True,
            "cross_layer_enforcement": True,
            "decision_precedence": True,
            "security_context_propagation": True,
            "final_enforcement_boundary": True,
            "security_state_propagation": True,
            "enterprise_integration_security": True,
            "fail_safe_recovery": True,
            "verification_engine": True,
            "execution_authority": False,
            "self_authorized_execution": False,
            "requires_human_approval": True,
            "executable": False,
        }
