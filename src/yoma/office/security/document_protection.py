from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocumentOperation(str, Enum):
    READ = "READ"
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    EXPORT = "EXPORT"


@dataclass(frozen=True)
class DocumentRequest:
    actor: str
    operation: DocumentOperation
    path: str
    classification: str = "INTERNAL"
    approved: bool = False


@dataclass(frozen=True)
class DocumentProtectionResult:
    allowed: bool
    decision: str
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DocumentProtection:
    def assess(self, request: DocumentRequest) -> DocumentProtectionResult:
        if not request.actor or not request.path:
            return DocumentProtectionResult(
                False, "DENY", "incomplete document request",
            )

        classification = request.classification.upper()

        if classification == "RESTRICTED" and not request.approved:
            return DocumentProtectionResult(
                False,
                "DENY",
                "restricted document requires explicit approval",
            )

        if request.operation in {
            DocumentOperation.DELETE,
            DocumentOperation.EXPORT,
        } and not request.approved:
            return DocumentProtectionResult(
                False,
                "REVIEW",
                "destructive or export document operation requires approval",
            )

        return DocumentProtectionResult(
            True,
            "GOVERNED",
            "document request satisfies current protection boundary",
        )
