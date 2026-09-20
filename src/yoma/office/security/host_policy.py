"""Host-level defensive security policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostSecurityPolicy:
    service_account_least_privilege: bool = True
    protected_installation: bool = True
    secret_isolation: bool = True
    binary_integrity: bool = True
    configuration_integrity: bool = True
    process_monitoring: bool = True
    filesystem_monitoring: bool = True
    network_loopback_default: bool = True
    adaptive_blocking: bool = True
    emergency_containment: bool = True
    human_review_for_remediation: bool = True
    ai_execution_authority: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "service_account_least_privilege": self.service_account_least_privilege,
            "protected_installation": self.protected_installation,
            "secret_isolation": self.secret_isolation,
            "binary_integrity": self.binary_integrity,
            "configuration_integrity": self.configuration_integrity,
            "process_monitoring": self.process_monitoring,
            "filesystem_monitoring": self.filesystem_monitoring,
            "network_loopback_default": self.network_loopback_default,
            "adaptive_blocking": self.adaptive_blocking,
            "emergency_containment": self.emergency_containment,
            "human_review_for_remediation": self.human_review_for_remediation,
            "ai_execution_authority": self.ai_execution_authority,
        }
