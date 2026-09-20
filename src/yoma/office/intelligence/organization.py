from __future__ import annotations

from collections import Counter
from typing import Any

from yoma.office.identity import SystemIdentity, UserIdentity


class OrganizationIntelligence:
    """
    Provider-neutral organization-level intelligence model.

    Consumes normalized organization identities and produces
    deterministic organization metrics.

    This layer does not make employment, disciplinary, financial,
    or security decisions.
    """

    def __init__(
        self,
        *,
        users: list[UserIdentity],
        systems: list[SystemIdentity],
    ) -> None:
        if not isinstance(users, list):
            raise TypeError("Users must be a list")

        if not isinstance(systems, list):
            raise TypeError("Systems must be a list")

        for user in users:
            if not isinstance(user, UserIdentity):
                raise TypeError("Users must contain UserIdentity objects")

        for system in systems:
            if not isinstance(system, SystemIdentity):
                raise TypeError(
                    "Systems must contain SystemIdentity objects"
                )

        self._users = list(users)
        self._systems = list(systems)

    # ------------------------------------------------------------------
    # User metrics
    # ------------------------------------------------------------------

    def total_users(self) -> int:
        return len(self._users)

    def active_users(self) -> int:
        return sum(user.active for user in self._users)

    def inactive_users(self) -> int:
        return sum(not user.active for user in self._users)

    # ------------------------------------------------------------------
    # System metrics
    # ------------------------------------------------------------------

    def total_systems(self) -> int:
        return len(self._systems)

    def active_systems(self) -> int:
        return sum(system.active for system in self._systems)

    def inactive_systems(self) -> int:
        return sum(not system.active for system in self._systems)

    # ------------------------------------------------------------------
    # Organizational dimensions
    # ------------------------------------------------------------------

    def departments(self) -> list[str]:
        return sorted(
            {
                user.department
                for user in self._users
                if user.department
            }
        )

    def users_by_department(self) -> dict[str, int]:
        counts = Counter(
            user.department
            for user in self._users
            if user.department
        )

        return dict(sorted(counts.items()))

    def roles(self) -> list[str]:
        return sorted(
            {
                user.role
                for user in self._users
                if user.role
            }
        )

    def users_by_role(self) -> dict[str, int]:
        counts = Counter(
            user.role
            for user in self._users
            if user.role
        )

        return dict(sorted(counts.items()))

    # ------------------------------------------------------------------
    # Organization snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "total_users": self.total_users(),
            "active_users": self.active_users(),
            "inactive_users": self.inactive_users(),
            "total_systems": self.total_systems(),
            "active_systems": self.active_systems(),
            "inactive_systems": self.inactive_systems(),
            "departments": self.departments(),
            "roles": self.roles(),
            "users_by_department": self.users_by_department(),
            "users_by_role": self.users_by_role(),
        }