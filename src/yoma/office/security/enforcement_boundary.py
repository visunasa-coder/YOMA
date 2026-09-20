from __future__ import annotations

from dataclasses import dataclass

from .unified_policy import SecurityEnforcementDecision, UnifiedSecurityDecision


@dataclass(frozen=True)
class EnforcementBoundaryResult:
    decision: str
    execution_authorized: bool
    requires_human_approval: bool
    reason: str


class FinalSecurityEnforcementBoundary:
    """
    Final gate before ApprovalExecutionBridge.

    IMPORTANT:
    This class never executes an action and never creates
    authorization by itself.
    """

    def evaluate(
        self,
        decision: UnifiedSecurityDecision,
        *,
        governed_authorization: bool = False,
    ) -> EnforcementBoundaryResult:

        if decision.decision is SecurityEnforcementDecision.DENY:
            return EnforcementBoundaryResult(
                decision="deny",
                execution_authorized=False,
                requires_human_approval=True,
                reason=decision.reason,
            )

        if decision.decision is SecurityEnforcementDecision.REVIEW:
            return EnforcementBoundaryResult(
                decision="review",
                execution_authorized=False,
                requires_human_approval=True,
                reason=decision.reason,
            )

        # Even an ALLOW from the security plane does not itself
        # authorize execution.
        if not governed_authorization:
            return EnforcementBoundaryResult(
                decision="review",
                execution_authorized=False,
                requires_human_approval=True,
                reason="governed_execution_authorization_required",
            )

        return EnforcementBoundaryResult(
            decision="allow",
            execution_authorized=False,
            requires_human_approval=True,
            reason="security_clearance_only_existing_governed_authorization_required",
        )
