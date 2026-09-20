"""Production hardening policy for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProductionHardeningResult:
    secure: bool
    configuration_valid: bool
    secrets_protected: bool
    execution_governed: bool
    failures_isolated: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "secure": self.secure,
            "configuration_valid": self.configuration_valid,
            "secrets_protected": self.secrets_protected,
            "execution_governed": self.execution_governed,
            "failures_isolated": self.failures_isolated,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ProductionHardening:
    """Read-only production readiness assessment."""

    def assess(
        self,
        *,
        configuration_valid: bool,
        secrets_protected: bool,
        execution_governed: bool,
        failures_isolated: bool,
        issues: tuple[str, ...] = (),
    ) -> ProductionHardeningResult:
        checks = (
            configuration_valid,
            secrets_protected,
            execution_governed,
            failures_isolated,
        )

        return ProductionHardeningResult(
            secure=all(checks),
            configuration_valid=configuration_valid,
            secrets_protected=secrets_protected,
            execution_governed=execution_governed,
            failures_isolated=failures_isolated,
            issues=tuple(issues),
        )
