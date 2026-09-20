from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityState:
    host_restricted: bool = False
    identity_restricted: bool = False
    incident_restricted: bool = False
    data_restricted: bool = False

    @property
    def restricted(self) -> bool:
        return (
            self.host_restricted
            or self.identity_restricted
            or self.incident_restricted
            or self.data_restricted
        )


class SecurityStatePropagator:
    def derive(
        self,
        *,
        host_state: str = "healthy",
        identity_state: str = "trusted",
        incident_severity: str = "info",
        data_state: str = "allowed",
    ) -> SecurityState:

        return SecurityState(
            host_restricted=host_state in {"restricted", "compromised"},
            identity_restricted=identity_state in {"restricted", "untrusted"},
            incident_restricted=incident_severity in {"high", "critical"},
            data_restricted=data_state in {"restricted", "blocked"},
        )
