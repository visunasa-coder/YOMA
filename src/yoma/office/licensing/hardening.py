"""Enterprise licensing hardening for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .activation import ActivationStatus
from .license_model import LicenseStatus, YomaLicense
from .license_validation import LicenseValidator
from .persistence import LicensePersistence, PersistedActivation


@dataclass(frozen=True)
class LicensingHardeningResult:
    """Immutable hardening assessment."""

    safe: bool
    license_id: str
    organization_id: str
    checks: tuple[str, ...]
    failures: tuple[str, ...]
    executable: bool = False
    requires_human_approval: bool = True


class LicensingHardening:
    """Perform deterministic safety checks around licensing state."""

    def __init__(self, persistence: LicensePersistence) -> None:
        self.persistence = persistence
        self.validator = LicenseValidator()

    def assess(
        self,
        license: YomaLicense,
        *,
        now: datetime | None = None,
    ) -> LicensingHardeningResult:
        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        checks: list[str] = []
        failures: list[str] = []

        checks.append("license_structure")

        validation = self.validator.validate(
            license,
            now=current,
        )

        if not validation.valid:
            failures.append(validation.reason)

        checks.append("license_validation")

        persisted = self.persistence.load()

        checks.append("persistent_state_integrity")

        if persisted is not None:
            if persisted.license_id != license.license_id:
                failures.append("persistent_license_mismatch")

            if persisted.organization_id != license.organization_id:
                failures.append("persistent_organization_mismatch")

            if (
                persisted.status is ActivationStatus.ACTIVE
                and not validation.valid
            ):
                failures.append("active_persistence_with_invalid_license")

        checks.append("identity_consistency")

        return LicensingHardeningResult(
            safe=not failures,
            license_id=license.license_id,
            organization_id=license.organization_id,
            checks=tuple(checks),
            failures=tuple(failures),
        )
