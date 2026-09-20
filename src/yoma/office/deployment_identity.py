"""Enterprise deployment identity and configuration for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeploymentIdentity:
    """Immutable identity and filesystem metadata for a YOMA deployment."""

    deployment_id: str
    organization_id: str
    edition: str
    version: str
    environment: str
    installation_path: Path
    configuration_path: Path

    def __post_init__(self) -> None:
        for field_name in (
            "deployment_id",
            "organization_id",
            "edition",
            "version",
            "environment",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if not isinstance(self.installation_path, Path):
            raise TypeError("installation_path must be a Path")

        if not isinstance(self.configuration_path, Path):
            raise TypeError("configuration_path must be a Path")

    @property
    def is_enterprise(self) -> bool:
        return self.edition.strip().lower() == "enterprise"

    def as_dict(self) -> dict[str, str]:
        """Return deterministic deployment metadata without secrets."""
        return {
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "edition": self.edition,
            "version": self.version,
            "environment": self.environment,
            "installation_path": str(self.installation_path),
            "configuration_path": str(self.configuration_path),
        }


@dataclass(frozen=True)
class DeploymentConfiguration:
    """Immutable environment-specific deployment configuration."""

    identity: DeploymentIdentity
    service_name: str = "YOMA"
    auto_start: bool = False

    def __post_init__(self) -> None:
        if not self.service_name.strip():
            raise ValueError("service_name must not be empty")

    def as_dict(self) -> dict[str, object]:
        """Return deployment configuration without secret material."""
        return {
            **self.identity.as_dict(),
            "service_name": self.service_name,
            "auto_start": self.auto_start,
        }
