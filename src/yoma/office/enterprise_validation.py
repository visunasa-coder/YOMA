"""M41.1 end-to-end enterprise validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class EnterpriseValidationResult:
    valid: bool
    events_valid: bool
    intelligence_valid: bool
    control_valid: bool
    background_valid: bool
    licensing_valid: bool
    deployment_valid: bool
    hardening_valid: bool
    execution_governed: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "events_valid": self.events_valid,
            "intelligence_valid": self.intelligence_valid,
            "control_valid": self.control_valid,
            "background_valid": self.background_valid,
            "licensing_valid": self.licensing_valid,
            "deployment_valid": self.deployment_valid,
            "hardening_valid": self.hardening_valid,
            "execution_governed": self.execution_governed,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class EnterpriseValidation:
    """Read-only end-to-end validation of YOMA enterprise layers."""

    def validate(
        self,
        *,
        events_valid: bool,
        intelligence_valid: bool,
        control_valid: bool,
        background_valid: bool,
        licensing_valid: bool,
        deployment_valid: bool,
        hardening_valid: bool,
        execution_governed: bool,
        issues: Iterable[str] = (),
    ) -> EnterpriseValidationResult:
        normalized_issues = tuple(
            dict.fromkeys(str(item) for item in issues)
        )

        checks = (
            events_valid,
            intelligence_valid,
            control_valid,
            background_valid,
            licensing_valid,
            deployment_valid,
            hardening_valid,
            execution_governed,
        )

        return EnterpriseValidationResult(
            valid=all(checks),
            events_valid=events_valid,
            intelligence_valid=intelligence_valid,
            control_valid=control_valid,
            background_valid=background_valid,
            licensing_valid=licensing_valid,
            deployment_valid=deployment_valid,
            hardening_valid=hardening_valid,
            execution_governed=execution_governed,
            issues=normalized_issues,
        )
