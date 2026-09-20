from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .base import (
    IdentityRegistryAdapter,
    SystemIdentity,
    UserIdentity,
)


@dataclass(frozen=True)
class IdentityManagerStatus:
    adapter: str
    healthy: bool


class IdentityRegistryManager:
    """
    Central identity access layer for YOMA.

    YOMA consumes organizational identity through an adapter and does
    not assume ownership of the company's authoritative user registry.
    """

    def __init__(self, adapter: IdentityRegistryAdapter) -> None:
        self.adapter = adapter

    @property
    def provider(self) -> str:
        return self.adapter.name

    def health(self) -> dict:
        result = self.adapter.health()

        if not isinstance(result, dict):
            return {
                "status": "unhealthy",
                "provider": self.provider,
            }

        return {
            **result,
            "provider": self.provider,
        }

    def status(self) -> IdentityManagerStatus:
        health = self.health()
        return IdentityManagerStatus(
            adapter=self.provider,
            healthy=health.get("status") in {"healthy", "ok"},
        )

    def get_user(self, user_id: str) -> Optional[UserIdentity]:
        normalized = str(user_id).strip()

        if not normalized:
            raise ValueError("user_id is required")

        return self.adapter.get_user(normalized)

    def list_users(self) -> list[UserIdentity]:
        return list(self.adapter.list_users())

    def resolve_user(self, external_id: str) -> Optional[UserIdentity]:
        normalized = str(external_id).strip()

        if not normalized:
            raise ValueError("external_id is required")

        return self.adapter.resolve_user(normalized)

    def get_system(self, system_id: str) -> Optional[SystemIdentity]:
        normalized = str(system_id).strip()

        if not normalized:
            raise ValueError("system_id is required")

        return self.adapter.get_system(normalized)

    def list_systems(self) -> list[SystemIdentity]:
        return list(self.adapter.list_systems())
