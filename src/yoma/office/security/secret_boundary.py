"""Secret isolation boundary.

This module deliberately does not store or print secret values.
Production Windows deployments should connect this boundary to
OS-backed protected credential storage.
"""

from __future__ import annotations

from dataclasses import dataclass


_SECRET_WORDS = (
    "password",
    "secret",
    "token",
    "credential",
    "authorization",
    "api_key",
    "apikey",
    "private_key",
    "client_secret",
)


def is_secret_name(name: str) -> bool:
    lowered = name.lower()
    return any(word in lowered for word in _SECRET_WORDS)


def redact_mapping(values: dict[str, object]) -> dict[str, object]:
    return {
        key: "[REDACTED]" if is_secret_name(key) else value
        for key, value in values.items()
    }


@dataclass(frozen=True)
class SecretBoundaryResult:
    safe: bool
    reason: str
    storage: str = "os_protected_storage_required"
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "safe": self.safe,
            "reason": self.reason,
            "storage": self.storage,
            "executable": self.executable,
        }


class SecretBoundary:
    def inspect_configuration(
        self,
        configuration: dict[str, object],
    ) -> SecretBoundaryResult:

        plaintext_keys = [
            key for key, value in configuration.items()
            if is_secret_name(key) and isinstance(value, str) and value
        ]

        if plaintext_keys:
            return SecretBoundaryResult(
                False,
                "secret-like configuration values require protected storage",
            )

        return SecretBoundaryResult(
            True,
            "no plaintext secret-like values detected",
        )
