from dataclasses import dataclass
from enum import Enum


class ZeroTrustDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


@dataclass(frozen=True)
class ZeroTrustContext:
    authenticated: bool
    authorized: bool
    trusted_device: bool
    active_session: bool
    threat_level: str
    resource: str
    approved: bool = False
    authorization_review: bool = False


@dataclass(frozen=True)
class ZeroTrustResult:
    decision: ZeroTrustDecision
    reason: str
    fail_closed: bool = True
    requires_human_approval: bool = True
    executable: bool = False


class ZeroTrustAccessEngine:
    def decide(self, context: ZeroTrustContext) -> ZeroTrustResult:

        if not context.authenticated:
            return ZeroTrustResult(
                ZeroTrustDecision.DENY,
                "authentication required",
            )

        if not context.authorized:
            if context.authorization_review and not context.approved:
                return ZeroTrustResult(
                    ZeroTrustDecision.REVIEW,
                    "authorization exists but human approval is pending",
                )

            return ZeroTrustResult(
                ZeroTrustDecision.DENY,
                "authorization denied",
            )

        if not context.trusted_device:
            return ZeroTrustResult(
                ZeroTrustDecision.DENY,
                "device trust requirement failed",
            )

        if not context.active_session:
            return ZeroTrustResult(
                ZeroTrustDecision.DENY,
                "active session required",
            )

        if context.threat_level.lower() in {"high", "critical"}:
            return ZeroTrustResult(
                ZeroTrustDecision.DENY,
                "elevated threat level",
            )

        if not context.approved:
            return ZeroTrustResult(
                ZeroTrustDecision.REVIEW,
                "human approval required",
            )

        return ZeroTrustResult(
            ZeroTrustDecision.ALLOW,
            "zero-trust conditions satisfied",
        )
