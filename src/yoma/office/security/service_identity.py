from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class ServiceIdentity:
    service_id: str
    provider: str
    scopes: FrozenSet[str]
    active: bool = True


@dataclass(frozen=True)
class ServiceIdentityResult:
    allowed: bool
    reason: str
    scope_valid: bool
    requires_human_approval: bool = True
    executable: bool = False


class ServiceIdentityGovernance:
    def evaluate(
        self,
        identity: ServiceIdentity,
        requested_scope: str,
        approved: bool = False,
    ) -> ServiceIdentityResult:

        if not identity.active:
            return ServiceIdentityResult(
                False,
                "service identity inactive",
                False,
            )

        if requested_scope not in identity.scopes:
            return ServiceIdentityResult(
                False,
                "requested integration scope is not granted",
                False,
            )

        if not approved:
            return ServiceIdentityResult(
                False,
                "integration access requires human approval",
                True,
            )

        return ServiceIdentityResult(
            True,
            "service identity scope satisfied",
            True,
        )
