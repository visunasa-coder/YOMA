"""License enforcement boundary for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .entitlements import LicenseEntitlementResolver
from .license_model import YomaLicense
from .license_validation import LicenseValidator


@dataclass(frozen=True)
class LicenseAccessDecision:
    """Immutable licensing access decision.

    This decision describes licensing availability only.
    It is deliberately not an execution authorization.
    """

    capability: str
    allowed: bool
    license_id: str
    organization_id: str
    reason: str
    requires_human_approval: bool = True
    executable: bool = False


class LicenseEnforcementBoundary:
    """Determine whether a capability is licensed."""

    def check(
        self,
        license: YomaLicense,
        capability: str,
        *,
        now: datetime | None = None,
    ) -> LicenseAccessDecision:
        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        validation = LicenseValidator().validate(
            license,
            now=current,
        )

        if not validation.valid:
            return LicenseAccessDecision(
                capability=capability,
                allowed=False,
                license_id=license.license_id,
                organization_id=license.organization_id,
                reason=f"license_invalid:{validation.reason}",
            )

        entitlement = LicenseEntitlementResolver().resolve(
            license,
            capability,
        )

        return LicenseAccessDecision(
            capability=capability,
            allowed=entitlement.entitled,
            license_id=license.license_id,
            organization_id=license.organization_id,
            reason=entitlement.reason,
        )
