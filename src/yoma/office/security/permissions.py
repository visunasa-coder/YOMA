from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


class PrivilegeLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass(frozen=True)
class PermissionSet:
    permissions: FrozenSet[str] = frozenset()
    privilege: PrivilegeLevel = PrivilegeLevel.READ


@dataclass(frozen=True)
class PermissionResult:
    decision: PermissionDecision
    reason: str
    least_privilege: bool
    requires_human_approval: bool = True
    executable: bool = False


class PermissionGovernance:
    def evaluate(
        self,
        requested_permission: str,
        granted_permissions: FrozenSet[str],
        resource_protected: bool = True,
        approved: bool = False,
    ) -> PermissionResult:

        if not requested_permission:
            return PermissionResult(
                PermissionDecision.DENY,
                "missing permission",
                True,
            )

        if requested_permission not in granted_permissions:
            return PermissionResult(
                PermissionDecision.DENY,
                "permission not granted",
                True,
            )

        if resource_protected and not approved:
            return PermissionResult(
                PermissionDecision.REVIEW,
                "protected resource requires human approval",
                True,
            )

        return PermissionResult(
            PermissionDecision.ALLOW,
            "permission satisfied",
            True,
        )
