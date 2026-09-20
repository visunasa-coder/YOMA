from dataclasses import dataclass
from enum import Enum


class PrivilegeDecision(str, Enum):
    DENY = "deny"
    REVIEW = "review"
    ALLOW = "allow"


@dataclass(frozen=True)
class PrivilegeRequest:
    identity_id: str
    requested_role: str
    resource: str
    justification: str
    approved: bool = False


@dataclass(frozen=True)
class PrivilegeResult:
    decision: PrivilegeDecision
    reason: str
    elevated: bool
    requires_human_approval: bool = True
    executable: bool = False


class PrivilegedAccessGovernance:
    def evaluate(self, request: PrivilegeRequest) -> PrivilegeResult:
        if not request.identity_id or not request.resource:
            return PrivilegeResult(
                PrivilegeDecision.DENY,
                "incomplete privilege request",
                False,
            )

        if not request.justification:
            return PrivilegeResult(
                PrivilegeDecision.DENY,
                "privilege justification required",
                False,
            )

        if not request.approved:
            return PrivilegeResult(
                PrivilegeDecision.REVIEW,
                "human approval required for privilege elevation",
                False,
            )

        return PrivilegeResult(
            PrivilegeDecision.ALLOW,
            "privilege request approved",
            True,
        )
