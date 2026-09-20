"""Minimal explicit RBAC boundary for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class SecurityRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    SERVICE = "service"
    READ_ONLY = "read_only"


@dataclass(frozen=True)
class SecurityIdentity:
    identity_id: str
    role: SecurityRole
    authenticated: bool = False
    active: bool = True

    def __post_init__(self) -> None:
        if not self.identity_id.strip():
            raise ValueError("identity_id is required")
        if not isinstance(self.role, SecurityRole):
            raise TypeError("role must be SecurityRole")


class RBAC:
    """Explicit permission checker. Never creates authorization."""

    def __init__(
        self,
        permissions: dict[SecurityRole, Iterable[str]] | None = None,
    ) -> None:
        self._permissions = {
            role: frozenset(values)
            for role, values in (permissions or {}).items()
        }

    def allowed(
        self,
        identity: SecurityIdentity,
        permission: str,
    ) -> bool:
        if not identity.authenticated or not identity.active:
            return False

        permission = permission.strip()
        if not permission:
            return False

        return permission in self._permissions.get(identity.role, frozenset())

    def permissions_for(self, role: SecurityRole) -> frozenset[str]:
        return self._permissions.get(role, frozenset())
