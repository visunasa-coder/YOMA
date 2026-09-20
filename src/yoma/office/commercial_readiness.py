"""Commercial release readiness assessment for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CommercialReadinessResult:
    ready: bool
    product_identity_valid: bool
    release_manifest_valid: bool
    integrity_available: bool
    licensing_ready: bool
    deployment_ready: bool
    hardening_ready: bool
    enterprise_validation_ready: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "product_identity_valid": self.product_identity_valid,
            "release_manifest_valid": self.release_manifest_valid,
            "integrity_available": self.integrity_available,
            "licensing_ready": self.licensing_ready,
            "deployment_ready": self.deployment_ready,
            "hardening_ready": self.hardening_ready,
            "enterprise_validation_ready": self.enterprise_validation_ready,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class CommercialReadiness:
    """Read-only assessment of commercial release readiness."""

    def assess(
        self,
        *,
        product_identity_valid: bool,
        release_manifest_valid: bool,
        integrity_available: bool,
        licensing_ready: bool,
        deployment_ready: bool,
        hardening_ready: bool,
        enterprise_validation_ready: bool,
        issues: Iterable[str] = (),
    ) -> CommercialReadinessResult:
        normalized_issues = tuple(
            dict.fromkeys(str(item) for item in issues)
        )

        checks = (
            product_identity_valid,
            release_manifest_valid,
            integrity_available,
            licensing_ready,
            deployment_ready,
            hardening_ready,
            enterprise_validation_ready,
        )

        return CommercialReadinessResult(
            ready=all(checks),
            product_identity_valid=product_identity_valid,
            release_manifest_valid=release_manifest_valid,
            integrity_available=integrity_available,
            licensing_ready=licensing_ready,
            deployment_ready=deployment_ready,
            hardening_ready=hardening_ready,
            enterprise_validation_ready=enterprise_validation_ready,
            issues=normalized_issues,
        )
