"""Commercial release candidate runtime for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from yoma.office.commercial_product import CommercialProductCatalog
from yoma.office.release_manifest import ReleaseManifest
from yoma.office.commercial_readiness import CommercialReadiness


@dataclass(frozen=True)
class ReleaseCandidateRuntimeResult:
    ready: bool
    product_valid: bool
    manifest_valid: bool
    integrity_valid: bool
    commercial_ready: bool
    release_candidate: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "product_valid": self.product_valid,
            "manifest_valid": self.manifest_valid,
            "integrity_valid": self.integrity_valid,
            "commercial_ready": self.commercial_ready,
            "release_candidate": self.release_candidate,
            "issues": list(self.issues),
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class CommercialReleaseCandidateRuntime:
    """Composes commercial release validation without executing release actions."""

    def assess(
        self,
        *,
        product_catalog: CommercialProductCatalog,
        release_manifest: ReleaseManifest,
        product_identity_valid: bool,
        release_manifest_valid: bool,
        integrity_available: bool,
        licensing_ready: bool,
        deployment_ready: bool,
        hardening_ready: bool,
        enterprise_validation_ready: bool,
        issues: Iterable[str] = (),
    ) -> ReleaseCandidateRuntimeResult:
        product = product_catalog.catalog()

        product_valid = (
            bool(product.get("product"))
            and bool(product.get("product", {}).get("product_name"))
            and bool(product.get("product", {}).get("product_version"))
            and product_identity_valid
        )

        manifest_data = release_manifest.as_dict()

        manifest_valid = (
            bool(manifest_data.get("product_name"))
            and bool(manifest_data.get("product_version"))
            and bool(manifest_data.get("release_channel"))
            and release_manifest_valid
        )

        integrity_valid = (
            integrity_available
            and len(release_manifest.integrity_sha256()) == 64
        )

        readiness = CommercialReadiness().assess(
            product_identity_valid=product_valid,
            release_manifest_valid=manifest_valid,
            integrity_available=integrity_valid,
            licensing_ready=licensing_ready,
            deployment_ready=deployment_ready,
            hardening_ready=hardening_ready,
            enterprise_validation_ready=enterprise_validation_ready,
            issues=tuple(issues),
        )

        combined_issues = tuple(
            dict.fromkeys(
                (
                    *readiness.issues,
                )
            )
        )

        ready = (
            product_valid
            and manifest_valid
            and integrity_valid
            and readiness.ready
        )

        return ReleaseCandidateRuntimeResult(
            ready=ready,
            product_valid=product_valid,
            manifest_valid=manifest_valid,
            integrity_valid=integrity_valid,
            commercial_ready=readiness.ready,
            release_candidate=ready,
            issues=combined_issues,
        )
