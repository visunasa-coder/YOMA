"""Unified licensing runtime for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .activation import (
    ActivationResult,
    ActivationStatus,
    LicenseActivationRuntime,
)
from .enforcement import (
    LicenseAccessDecision,
    LicenseEnforcementBoundary,
)
from .entitlements import LicenseEntitlementResolver
from .license_model import YomaLicense
from .license_validation import (
    LicenseValidationResult,
    LicenseValidator,
)
from .persistence import LicensePersistence, PersistedActivation


@dataclass(frozen=True)
class LicensingRuntimeResult:
    """Immutable unified licensing runtime result."""

    license_id: str
    organization_id: str
    validation: LicenseValidationResult
    activation: ActivationResult
    access: LicenseAccessDecision | None
    entitled_capabilities: tuple[str, ...]
    active: bool
    requires_human_approval: bool = True
    executable: bool = False


class LicensingRuntime:
    """Unified governed runtime for YOMA licensing."""

    def __init__(self, persistence: LicensePersistence) -> None:
        self.persistence = persistence
        self.validator = LicenseValidator()
        self.activation = LicenseActivationRuntime()
        self.entitlements = LicenseEntitlementResolver()
        self.enforcement = LicenseEnforcementBoundary()

    def activate(
        self,
        license: YomaLicense,
        *,
        now: datetime | None = None,
    ) -> LicensingRuntimeResult:
        """Validate, activate, and persist a license."""

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        validation = self.validator.validate(
            license,
            now=current,
        )

        activation_result = self.activation.activate(
            license,
            now=current,
        )

        if activation_result.changed and activation_result.status is ActivationStatus.ACTIVE:
            self.persistence.save(
                PersistedActivation(
                    license_id=license.license_id,
                    organization_id=license.organization_id,
                    status=activation_result.status,
                    activated_at=(
                        activation_result.activated_at.isoformat()
                        if activation_result.activated_at is not None
                        else None
                    ),
                )
            )

        access = self.enforcement.check(
            license,
            next(iter(license.entitlements), ""),
            now=current,
        ) if license.entitlements else None

        return LicensingRuntimeResult(
            license_id=license.license_id,
            organization_id=license.organization_id,
            validation=validation,
            activation=activation_result,
            access=access,
            entitled_capabilities=self.entitlements.entitled_capabilities(
                license
            ),
            active=self.activation.is_active,
        )

    def check(
        self,
        license: YomaLicense,
        capability: str,
        *,
        now: datetime | None = None,
    ) -> LicenseAccessDecision:
        """Check licensing access for one capability."""

        return self.enforcement.check(
            license,
            capability,
            now=now,
        )

    def deactivate(
        self,
        *,
        now: datetime | None = None,
    ) -> ActivationResult:
        """Deactivate and persist the current activation state."""

        result = self.activation.deactivate(now=now)

        if result.changed:
            self.persistence.save(
                PersistedActivation(
                    license_id=result.license_id,
                    organization_id=result.organization_id,
                    status=result.status,
                    activated_at=None,
                )
            )

        return result

    def recover(self) -> PersistedActivation | None:
        """Recover persisted activation state.

        Recovery restores state information only. It does not validate
        or silently authorize execution.
        """

        return self.persistence.load()

    def reset(self) -> None:
        """Reset in-memory and persisted licensing state."""

        self.activation.reset()
        self.persistence.clear()
