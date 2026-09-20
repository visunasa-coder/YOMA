from __future__ import annotations

from yoma.office.identity import (
    IdentityRegistryManager,
    SystemIdentity,
    UserIdentity,
)


class OrganizationIdentity:
    """Normalized organizational identity view for YOMA."""

    def __init__(self, manager: IdentityRegistryManager) -> None:
        if manager is None:
            raise ValueError("Identity manager is required")

        self.manager = manager

    @property
    def provider(self) -> str:
        return self.manager.provider

    def users(self) -> list[UserIdentity]:
        return list(self.manager.list_users())

    def user(self, user_id: str) -> UserIdentity | None:
        return self.manager.get_user(user_id)

    def resolve_user(self, external_id: str) -> UserIdentity | None:
        return self.manager.resolve_user(external_id)

    def systems(self) -> list[SystemIdentity]:
        return list(self.manager.list_systems())

    def system(self, system_id: str) -> SystemIdentity | None:
        return self.manager.get_system(system_id)

    def departments(self) -> list[str]:
        departments = {
            user.department
            for user in self.users()
            if user.department
        }

        return sorted(departments)

    def roles(self) -> list[str]:
        roles = {
            user.role
            for user in self.users()
            if user.role
        }

        return sorted(roles)
