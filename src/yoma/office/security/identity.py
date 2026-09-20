from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class IdentityType(str, Enum):
    HUMAN = "human"
    SERVICE = "service"
    DEVICE = "device"
    INTEGRATION = "integration"


class TrustState(str, Enum):
    UNKNOWN = "unknown"
    UNTRUSTED = "untrusted"
    LIMITED = "limited"
    TRUSTED = "trusted"


@dataclass(frozen=True)
class EnterpriseIdentity:
    identity_id: str
    identity_type: IdentityType
    subject: str
    roles: FrozenSet[str] = frozenset()
    permissions: FrozenSet[str] = frozenset()
    trust: TrustState = TrustState.UNKNOWN
    authenticated: bool = False
    active: bool = True

    def __post_init__(self):
        if not self.identity_id or not self.subject:
            raise ValueError("identity_id and subject are required")


class IdentityRegistry:
    def __init__(self):
        self._identities = {}

    def register(self, identity: EnterpriseIdentity):
        self._identities[identity.identity_id] = identity
        return identity

    def get(self, identity_id: str):
        return self._identities.get(identity_id)

    def revoke(self, identity_id: str):
        identity = self._identities.get(identity_id)
        if not identity:
            return False
        self._identities[identity_id] = EnterpriseIdentity(
            identity_id=identity.identity_id,
            identity_type=identity.identity_type,
            subject=identity.subject,
            roles=identity.roles,
            permissions=identity.permissions,
            trust=TrustState.UNTRUSTED,
            authenticated=False,
            active=False,
        )
        return True
