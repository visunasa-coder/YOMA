"""YOMA v1.0 production release gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ProductionReleaseGateResult:
    approved: bool
    identity_valid: bool
    commercial_candidate_valid: bool
    enterprise_validation_valid: bool
    deployment_valid: bool
    hardening_valid: bool
    licensing_valid: bool
    gate_passed: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "identity_valid": self.identity_valid,
            "commercial_candidate_valid": self.commercial_candidate_valid,
            "enterprise_validation_valid": self.enterprise_validation_valid,
            "deployment_valid": self.deployment_valid,
            "hardening_valid": self.hardening_valid,
            "licensing_valid": self.licensing_valid,
            "gate_passed": self.gate_passed,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ProductionReleaseGate:
    """Read-only production release gate."""

    def assess(
        self,
        *,
        identity_valid: bool,
        commercial_candidate_valid: bool,
        enterprise_validation_valid: bool,
        deployment_valid: bool,
        hardening_valid: bool,
        licensing_valid: bool,
        issues: Iterable[str] = (),
    ) -> ProductionReleaseGateResult:
        normalized_issues = tuple(
            dict.fromkeys(str(item) for item in issues)
        )

        checks = (
            identity_valid,
            commercial_candidate_valid,
            enterprise_validation_valid,
            deployment_valid,
            hardening_valid,
            licensing_valid,
        )

        gate_passed = all(checks)

        return ProductionReleaseGateResult(
            approved=False,
            identity_valid=identity_valid,
            commercial_candidate_valid=commercial_candidate_valid,
            enterprise_validation_valid=enterprise_validation_valid,
            deployment_valid=deployment_valid,
            hardening_valid=hardening_valid,
            licensing_valid=licensing_valid,
            gate_passed=gate_passed,
            issues=normalized_issues,
        )
