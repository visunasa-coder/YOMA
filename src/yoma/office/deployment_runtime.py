"""Enterprise deployment runtime for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DeploymentRuntimeResult:
    deployment_id: str
    organization_id: str
    ready: bool
    healthy: bool
    installed: bool
    upgrade_allowed: bool
    recovery_required: bool
    package_integrity: bool
    secret_boundary_valid: bool
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "ready": self.ready,
            "healthy": self.healthy,
            "installed": self.installed,
            "upgrade_allowed": self.upgrade_allowed,
            "recovery_required": self.recovery_required,
            "package_integrity": self.package_integrity,
            "secret_boundary_valid": self.secret_boundary_valid,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class EnterpriseDeploymentRuntime:
    """Compose deployment health and recovery readiness without executing changes."""

    def assess(
        self,
        *,
        deployment_id: str,
        organization_id: str,
        installed: bool,
        installation_state: str,
        service_health: Mapping[str, Any],
        package_integrity: bool,
        secret_boundary_valid: bool,
        recovery_required: bool = False,
    ) -> DeploymentRuntimeResult:
        healthy = (
            installed
            and service_health.get("healthy") is True
            and service_health.get("service_state") == "running"
            and service_health.get("runtime_state") == "running"
            and service_health.get("runtime_running") is True
            and package_integrity
            and secret_boundary_valid
        )

        upgrade_allowed = (
            installed
            and not recovery_required
            and package_integrity
            and secret_boundary_valid
        )

        ready = healthy and not recovery_required

        if recovery_required:
            reason = "recovery required"
        elif not installed:
            reason = "deployment is not installed"
        elif not package_integrity:
            reason = "package integrity check failed"
        elif not secret_boundary_valid:
            reason = "secret boundary validation failed"
        elif not healthy:
            reason = "deployment service is not healthy"
        else:
            reason = "deployment ready"

        return DeploymentRuntimeResult(
            deployment_id=deployment_id,
            organization_id=organization_id,
            ready=ready,
            healthy=healthy,
            installed=installed,
            upgrade_allowed=upgrade_allowed,
            recovery_required=recovery_required,
            package_integrity=package_integrity,
            secret_boundary_valid=secret_boundary_valid,
            reason=reason,
        )
