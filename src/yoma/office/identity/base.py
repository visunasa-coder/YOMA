from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SystemIdentity:
    system_id: str
    name: Optional[str] = None
    system_number: Optional[str] = None
    active: bool = True


@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    system_id: Optional[str] = None
    active: bool = True


class IdentityRegistryAdapter(ABC):
    """
    Provider-neutral identity/registry contract.

    The company remains authoritative for its users and systems.
    YOMA consumes normalized identity information through this boundary.
    """

    name: str = "unknown"
    category: str = "identity_registry"

    @abstractmethod
    def health(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[UserIdentity]:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[UserIdentity]:
        raise NotImplementedError

    @abstractmethod
    def get_system(self, system_id: str) -> Optional[SystemIdentity]:
        raise NotImplementedError

    @abstractmethod
    def list_systems(self) -> list[SystemIdentity]:
        raise NotImplementedError

    @abstractmethod
    def resolve_user(self, external_id: str) -> Optional[UserIdentity]:
        raise NotImplementedError
