from dataclasses import dataclass
from enum import Enum
from typing import Any


class DLPDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class DLPAssessment:
    decision: DLPDecision
    reason: str
    destination: str
    sensitive_data_detected: bool
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "destination": self.destination,
            "sensitive_data_detected": self.sensitive_data_detected,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DataLossPrevention:
    def assess(
        self,
        *,
        destination: str,
        sensitive_data_detected: bool,
        classification: str,
        approved: bool = False,
    ) -> DLPAssessment:
        destination = destination.strip().lower()
        protected = classification.upper() in {"CONFIDENTIAL", "RESTRICTED"}

        if sensitive_data_detected and protected and not approved:
            return DLPAssessment(
                DLPDecision.BLOCK,
                "sensitive protected data cannot be exported without approval",
                destination,
                True,
            )

        if sensitive_data_detected and not approved:
            return DLPAssessment(
                DLPDecision.REVIEW,
                "sensitive data requires review before transmission",
                destination,
                True,
            )

        if not destination:
            return DLPAssessment(
                DLPDecision.BLOCK,
                "destination is required",
                destination,
                sensitive_data_detected,
            )

        return DLPAssessment(
            DLPDecision.ALLOW,
            "transmission satisfies current data policy",
            destination,
            sensitive_data_detected,
        )
