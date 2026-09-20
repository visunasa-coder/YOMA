from dataclasses import dataclass
from enum import Enum
from typing import Any


class DatabaseOperation(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class DatabaseRequest:
    actor: str
    operation: DatabaseOperation
    resource: str
    purpose: str
    approved: bool = False


@dataclass(frozen=True)
class DatabaseProtectionResult:
    allowed: bool
    decision: str
    reason: str
    adapter_required: bool = True
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "reason": self.reason,
            "adapter_required": self.adapter_required,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DatabaseProtection:
    def assess(self, request: DatabaseRequest) -> DatabaseProtectionResult:
        if not request.actor or not request.resource or not request.purpose:
            return DatabaseProtectionResult(
                False, "DENY", "incomplete database request",
            )

        if request.operation in {
            DatabaseOperation.WRITE,
            DatabaseOperation.DELETE,
            DatabaseOperation.ADMIN,
        } and not request.approved:
            return DatabaseProtectionResult(
                False,
                "REVIEW",
                "mutating database operation requires human approval",
            )

        if request.operation == DatabaseOperation.READ:
            return DatabaseProtectionResult(
                True,
                "ALLOW",
                "read request may proceed only through a governed database adapter",
            )

        return DatabaseProtectionResult(
            True,
            "GOVERNED",
            "approved database operation remains inside controlled adapter boundary",
        )
