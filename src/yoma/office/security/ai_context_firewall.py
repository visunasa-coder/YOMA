from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class AIContextDecision(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class AIContextAssessment:
    decision: AIContextDecision
    reason: str
    allowed_fields: tuple[str, ...]
    sensitive_findings: int
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "allowed_fields": list(self.allowed_fields),
            "sensitive_findings": self.sensitive_findings,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class AIContextFirewall:
    def inspect(
        self,
        context: Mapping[str, Any],
        *,
        classification: str,
        sensitive_findings: int,
        approved: bool = False,
    ) -> AIContextAssessment:
        protected = classification.upper() in {"CONFIDENTIAL", "RESTRICTED"}

        if sensitive_findings > 0 and protected and not approved:
            return AIContextAssessment(
                AIContextDecision.REDACT,
                "sensitive protected content must be minimized before AI context use",
                tuple(),
                sensitive_findings,
            )

        if classification.upper() == "RESTRICTED" and not approved:
            return AIContextAssessment(
                AIContextDecision.BLOCK,
                "restricted content cannot enter AI context without approval",
                tuple(),
                sensitive_findings,
            )

        if sensitive_findings > 0:
            return AIContextAssessment(
                AIContextDecision.REVIEW,
                "sensitive content requires controlled context handling",
                tuple(context.keys()),
                sensitive_findings,
            )

        return AIContextAssessment(
            AIContextDecision.ALLOW,
            "context contains no detected sensitive findings",
            tuple(context.keys()),
            0,
        )
