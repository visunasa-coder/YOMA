from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SecurityContext:
    actor_id: str
    identity_trusted: bool
    device_trusted: bool
    session_valid: bool
    request_id: str
    source_id: str
    data_classification: str = "public"
    threat_level: str = "none"
    host_state: str = "healthy"
    permissions: tuple[str, ...] = field(default_factory=tuple)
    approval_id: str | None = None

    def can_continue(self) -> bool:
        return (
            bool(self.actor_id)
            and bool(self.request_id)
            and self.identity_trusted
            and self.device_trusted
            and self.session_valid
            and self.host_state == "healthy"
            and self.threat_level not in {"high", "critical"}
        )

    def as_dict(self) -> dict:
        return {
            "actor_id": self.actor_id,
            "identity_trusted": self.identity_trusted,
            "device_trusted": self.device_trusted,
            "session_valid": self.session_valid,
            "request_id": self.request_id,
            "source_id": self.source_id,
            "data_classification": self.data_classification,
            "threat_level": self.threat_level,
            "host_state": self.host_state,
            "permissions": list(self.permissions),
            "approval_id": self.approval_id,
        }
