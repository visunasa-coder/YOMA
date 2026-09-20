"""Host identity and least-privilege boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HostTrustState(str, Enum):
    UNKNOWN = "unknown"
    TRUSTED = "trusted"
    RESTRICTED = "restricted"
    COMPROMISED = "compromised"


@dataclass(frozen=True)
class HostIdentity:
    deployment_id: str
    service_name: str
    account_name: str
    interactive_logon_allowed: bool = False
    administrator_required: bool = False

    def __post_init__(self) -> None:
        if not self.deployment_id.strip():
            raise ValueError("deployment_id required")
        if not self.service_name.strip():
            raise ValueError("service_name required")
        if not self.account_name.strip():
            raise ValueError("account_name required")

    @property
    def least_privilege_compliant(self) -> bool:
        return (
            not self.interactive_logon_allowed
            and not self.administrator_required
        )


@dataclass(frozen=True)
class HostAccessAssessment:
    allowed: bool
    trust_state: HostTrustState
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "trust_state": self.trust_state.value,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class HostAccessBoundary:
    def assess(
        self,
        identity: HostIdentity,
        trust_state: HostTrustState,
    ) -> HostAccessAssessment:

        if trust_state is HostTrustState.COMPROMISED:
            return HostAccessAssessment(
                False,
                trust_state,
                "host marked compromised",
            )

        if trust_state is HostTrustState.RESTRICTED:
            return HostAccessAssessment(
                False,
                trust_state,
                "host is in restricted mode",
            )

        if not identity.least_privilege_compliant:
            return HostAccessAssessment(
                False,
                trust_state,
                "host service identity violates least-privilege policy",
            )

        if trust_state is HostTrustState.UNKNOWN:
            return HostAccessAssessment(
                False,
                trust_state,
                "host trust has not been established",
            )

        return HostAccessAssessment(
            True,
            trust_state,
            "host satisfies configured access boundary",
        )
