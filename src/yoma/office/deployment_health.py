"""Enterprise deployment health and diagnostics for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DeploymentHealthResult:
    healthy: bool
    deployment_id: str
    organization_id: str
    installation_state: str
    service_state: str
    runtime_state: str
    package_integrity: bool
    secret_boundary_valid: bool
    diagnostics: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        for name in (
            "deployment_id",
            "organization_id",
            "installation_state",
            "service_state",
            "runtime_state",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty")

        if not isinstance(self.package_integrity, bool):
            raise TypeError("package_integrity must be a boolean")

        if not isinstance(self.secret_boundary_valid, bool):
            raise TypeError("secret_boundary_valid must be a boolean")

        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be a tuple")

        if self.requires_human_approval is not True:
            raise ValueError("deployment health must require human approval")

        if self.executable is not False:
            raise ValueError("deployment health must not be executable")

    def as_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "installation_state": self.installation_state,
            "service_state": self.service_state,
            "runtime_state": self.runtime_state,
            "package_integrity": self.package_integrity,
            "secret_boundary_valid": self.secret_boundary_valid,
            "diagnostics": list(self.diagnostics),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DeploymentHealth:
    """Read-only aggregator for enterprise deployment health."""

    def assess(
        self,
        *,
        deployment_id: str,
        organization_id: str,
        installation_state: str,
        service_health: Mapping[str, Any],
        package_integrity: bool,
        secret_boundary_valid: bool,
        diagnostics: tuple[str, ...] = (),
    ) -> DeploymentHealthResult:
        if not isinstance(service_health, Mapping):
            raise TypeError("service_health must be a mapping")

        healthy = (
            installation_state in {"installed", "upgraded", "repaired"}
            and service_health.get("healthy") is True
            and service_health.get("service_state") == "running"
            and service_health.get("runtime_state") == "running"
            and service_health.get("runtime_running") is True
            and package_integrity is True
            and secret_boundary_valid is True
        )

        return DeploymentHealthResult(
            healthy=healthy,
            deployment_id=deployment_id,
            organization_id=organization_id,
            installation_state=installation_state,
            service_state=str(service_health.get("service_state", "unknown")),
            runtime_state=str(service_health.get("runtime_state", "unknown")),
            package_integrity=package_integrity,
            secret_boundary_valid=secret_boundary_valid,
            diagnostics=tuple(diagnostics),
        )

    def diagnostics(
        self,
        result: DeploymentHealthResult,
    ) -> dict[str, Any]:
        """Return safe deployment diagnostics without secret material."""
        return {
            "healthy": result.healthy,
            "deployment_id": result.deployment_id,
            "organization_id": result.organization_id,
            "installation_state": result.installation_state,
            "service_state": result.service_state,
            "runtime_state": result.runtime_state,
            "package_integrity": result.package_integrity,
            "secret_boundary_valid": result.secret_boundary_valid,
            "diagnostics": list(result.diagnostics),
            "requires_human_approval": True,
            "executable": False,
        }
