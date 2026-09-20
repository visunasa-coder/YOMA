"""License validation for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .license_model import LicenseStatus, ProductEdition, YomaLicense


@dataclass(frozen=True)
class LicenseValidationResult:
    """Deterministic result of validating a YOMA license."""

    valid: bool
    license_id: str
    organization_id: str
    reason: str


class LicenseValidator:
    """Validate a canonical YOMA license without activating it."""

    def validate(
        self,
        license: YomaLicense,
        *,
        now: datetime | None = None,
    ) -> LicenseValidationResult:
        if not isinstance(license, YomaLicense):
            raise TypeError("license must be a YomaLicense")

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        if license.status is not LicenseStatus.ACTIVE:
            return LicenseValidationResult(
                valid=False,
                license_id=license.license_id,
                organization_id=license.organization_id,
                reason=f"license_status:{license.status.value}",
            )

        if license.is_expired(now=current):
            return LicenseValidationResult(
                valid=False,
                license_id=license.license_id,
                organization_id=license.organization_id,
                reason="license_expired",
            )

        if not isinstance(license.edition, ProductEdition):
            return LicenseValidationResult(
                valid=False,
                license_id=license.license_id,
                organization_id=license.organization_id,
                reason="invalid_edition",
            )

        return LicenseValidationResult(
            valid=True,
            license_id=license.license_id,
            organization_id=license.organization_id,
            reason="license_valid",
        )
