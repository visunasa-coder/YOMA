from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationSecurityResult:
    integration: str
    allowed: bool
    requires_human_approval: bool
    executable: bool
    reason: str


class EnterpriseIntegrationSecurity:
    SUPPORTED = frozenset({
        "gmail",
        "calendar",
        "contacts",
        "database",
        "files",
        "attendance",
        "external_api",
        "office_system",
    })

    def evaluate(
        self,
        integration: str,
        *,
        identity_allowed: bool,
        data_allowed: bool,
        threat_safe: bool,
        approved: bool = False,
    ) -> IntegrationSecurityResult:

        name = integration.strip().lower()

        if name not in self.SUPPORTED:
            return IntegrationSecurityResult(
                name, False, True, False, "unsupported_integration"
            )

        if not identity_allowed:
            return IntegrationSecurityResult(
                name, False, True, False, "identity_denied"
            )

        if not threat_safe:
            return IntegrationSecurityResult(
                name, False, True, False, "threat_boundary_denied"
            )

        if not data_allowed:
            return IntegrationSecurityResult(
                name, False, True, False, "data_policy_denied"
            )

        return IntegrationSecurityResult(
            name,
            True,
            True,
            False,
            "integration_security_clearance_only",
        )
