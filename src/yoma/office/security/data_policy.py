from dataclasses import dataclass
from enum import Enum
from typing import Any


class DataAccessDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class DataAccessPolicy:
    actor: str
    purpose: str
    classification: str
    operation: str
    approved: bool = False
    least_privilege: bool = True


@dataclass(frozen=True)
class DataAccessPolicyResult:
    decision: DataAccessDecision
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DataAccessPolicyEngine:
    def evaluate(self, policy: DataAccessPolicy) -> DataAccessPolicyResult:
        if not policy.actor or not policy.purpose or not policy.operation:
            return DataAccessPolicyResult(
                DataAccessDecision.DENY,
                "missing access context",
            )

        if not policy.least_privilege:
            return DataAccessPolicyResult(
                DataAccessDecision.DENY,
                "least privilege requirement not satisfied",
            )

        classification = policy.classification.upper()

        if classification == "PUBLIC":
            return DataAccessPolicyResult(
                DataAccessDecision.ALLOW,
                "public data within policy",
            )

        if classification == "INTERNAL":
            return DataAccessPolicyResult(
                DataAccessDecision.REVIEW,
                "internal data requires policy review",
            )

        if classification in {"CONFIDENTIAL", "RESTRICTED"}:
            if not policy.approved:
                return DataAccessPolicyResult(
                    DataAccessDecision.DENY,
                    "protected data requires explicit human approval",
                )

            return DataAccessPolicyResult(
                DataAccessDecision.REVIEW,
                "approved protected-data request remains governed",
            )

        return DataAccessPolicyResult(
            DataAccessDecision.DENY,
            "unknown classification",
        )
