"""YOMA v1.0 production release runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from yoma.office.production_release_identity import (
    ProductionReleaseIdentity,
    ProductionReleaseIdentityValidator,
)
from yoma.office.production_release_gate import ProductionReleaseGate
from yoma.office.production_release_safety import ProductionReleaseSafety


@dataclass(frozen=True)
class ProductionReleaseRuntimeResult:
    ready: bool
    identity_valid: bool
    release_gate_passed: bool
    safety_valid: bool
    commercial_candidate_valid: bool
    production_release: bool
    release_authorized: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "identity_valid": self.identity_valid,
            "release_gate_passed": self.release_gate_passed,
            "safety_valid": self.safety_valid,
            "commercial_candidate_valid": self.commercial_candidate_valid,
            "production_release": self.production_release,
            "release_authorized": self.release_authorized,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ProductionReleaseRuntime:
    """Final read-only YOMA v1.0 production release assessment."""

    def assess(
        self,
        *,
        identity: ProductionReleaseIdentity,
        commercial_candidate_valid: bool,
        enterprise_validation_valid: bool,
        deployment_valid: bool,
        hardening_valid: bool,
        licensing_valid: bool,
        release_authorized: bool = False,
        human_approval_required: bool = True,
        explicit_authorization_required: bool = True,
        execution_blocked: bool = True,
        autonomous_release_blocked: bool = True,
        issues: Iterable[str] = (),
    ) -> ProductionReleaseRuntimeResult:
        identity_valid = ProductionReleaseIdentityValidator().validate(identity)

        gate = ProductionReleaseGate().assess(
            identity_valid=identity_valid,
            commercial_candidate_valid=commercial_candidate_valid,
            enterprise_validation_valid=enterprise_validation_valid,
            deployment_valid=deployment_valid,
            hardening_valid=hardening_valid,
            licensing_valid=licensing_valid,
            issues=tuple(issues),
        )

        safety = ProductionReleaseSafety().assess(
            human_approval_required=human_approval_required,
            explicit_authorization_required=explicit_authorization_required,
            execution_blocked=execution_blocked,
            autonomous_release_blocked=autonomous_release_blocked,
            release_authorized=release_authorized,
            issues=gate.issues,
        )

        combined_issues = tuple(
            dict.fromkeys(
                (
                    *gate.issues,
                    *safety.issues,
                )
            )
        )

        ready = (
            identity_valid
            and gate.gate_passed
            and safety.safe
            and commercial_candidate_valid
        )

        return ProductionReleaseRuntimeResult(
            ready=ready,
            identity_valid=identity_valid,
            release_gate_passed=gate.gate_passed,
            safety_valid=safety.safe,
            commercial_candidate_valid=commercial_candidate_valid,
            production_release=ready,
            release_authorized=release_authorized,
            issues=combined_issues,
        )
