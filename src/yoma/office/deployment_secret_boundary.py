"""Enterprise configuration and secret boundary for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


_SECRET_FIELD_NAMES = frozenset(
    {
        "password",
        "secret",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "token",
        "credential",
        "credential_value",
        "master_key",
        "private_key",
    }
)


@dataclass(frozen=True)
class SecretReference:
    """Reference to secret material held outside deployment configuration."""

    name: str
    provider: str = "credential_vault"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("secret reference name must not be empty")

        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("secret reference provider must not be empty")

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class DeploymentSecretBoundary:
    """Governed boundary between non-secret configuration and secret material."""

    secret_references: tuple[SecretReference, ...] = ()

    def references(self) -> tuple[str, ...]:
        return tuple(reference.name for reference in self.secret_references)

    def as_dict(self) -> dict[str, object]:
        """Return references only; never return secret values."""
        return {
            "secret_references": [
                reference.as_dict()
                for reference in self.secret_references
            ]
        }

    @staticmethod
    def contains_secret_fields(configuration: Mapping[str, Any]) -> bool:
        """Detect fields that must not cross the deployment configuration boundary."""
        return any(
            str(key).strip().lower() in _SECRET_FIELD_NAMES
            for key in configuration
        )

    @staticmethod
    def sanitize(configuration: Mapping[str, Any]) -> dict[str, Any]:
        """Return a copy containing only non-secret configuration fields."""
        return {
            str(key): value
            for key, value in configuration.items()
            if str(key).strip().lower() not in _SECRET_FIELD_NAMES
        }

    def validate_configuration(
        self,
        configuration: Mapping[str, Any],
    ) -> None:
        """Reject configuration containing secret values."""
        if not isinstance(configuration, Mapping):
            raise TypeError("configuration must be a mapping")

        if self.contains_secret_fields(configuration):
            raise ValueError(
                "secret material must not be stored in deployment configuration"
            )
