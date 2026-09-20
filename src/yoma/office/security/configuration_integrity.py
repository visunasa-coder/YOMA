"""Configuration integrity state tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigurationSnapshot:
    configuration_id: str
    digest: str

    def __post_init__(self) -> None:
        if not self.configuration_id.strip():
            raise ValueError("configuration_id required")
        if not self.digest.strip():
            raise ValueError("digest required")


@dataclass(frozen=True)
class ConfigurationIntegrityResult:
    intact: bool
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "intact": self.intact,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ConfigurationIntegrity:
    def compare(
        self,
        baseline: ConfigurationSnapshot,
        current: ConfigurationSnapshot,
    ) -> ConfigurationIntegrityResult:

        if baseline.configuration_id != current.configuration_id:
            return ConfigurationIntegrityResult(
                False,
                "configuration identity mismatch",
            )

        if baseline.digest != current.digest:
            return ConfigurationIntegrityResult(
                False,
                "configuration digest changed",
            )

        return ConfigurationIntegrityResult(
            True,
            "configuration integrity verified",
        )
