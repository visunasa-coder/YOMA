"""YOMA emergency restricted-mode controller."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HostOperationalState(str, Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    INCIDENT = "incident"


@dataclass(frozen=True)
class ContainmentResult:
    state: HostOperationalState
    reason: str
    sensitive_execution_allowed: bool = False
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "reason": self.reason,
            "sensitive_execution_allowed": self.sensitive_execution_allowed,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class EmergencyContainment:
    def __init__(self) -> None:
        self._state = HostOperationalState.NORMAL
        self._reason = "normal operation"

    @property
    def state(self) -> HostOperationalState:
        return self._state

    def enter_restricted(self, reason: str) -> ContainmentResult:
        self._state = HostOperationalState.RESTRICTED
        self._reason = reason

        return ContainmentResult(
            HostOperationalState.RESTRICTED,
            reason,
            sensitive_execution_allowed=False,
        )

    def declare_incident(self, reason: str) -> ContainmentResult:
        self._state = HostOperationalState.INCIDENT
        self._reason = reason

        return ContainmentResult(
            HostOperationalState.INCIDENT,
            reason,
            sensitive_execution_allowed=False,
        )

    def recover(self, approved: bool = False) -> ContainmentResult:
        if not approved:
            return ContainmentResult(
                self._state,
                "human approval required for recovery",
                sensitive_execution_allowed=False,
            )

        self._state = HostOperationalState.NORMAL
        self._reason = "recovered through governed review"

        return ContainmentResult(
            HostOperationalState.NORMAL,
            self._reason,
            sensitive_execution_allowed=False,
        )
