"""License activation lifecycle for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .license_model import YomaLicense
from .license_validation import LicenseValidator


class ActivationStatus(str, Enum):
    """Activation lifecycle state."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


@dataclass(frozen=True)
class ActivationResult:
    """Immutable result of an activation lifecycle operation."""

    license_id: str
    organization_id: str
    status: ActivationStatus
    changed: bool
    reason: str
    activated_at: datetime | None = None


class LicenseActivationRuntime:
    """Manage activation state for a validated YOMA license."""

    def __init__(self) -> None:
        self._status = ActivationStatus.INACTIVE
        self._license_id: str | None = None
        self._organization_id: str | None = None
        self._activated_at: datetime | None = None

    @property
    def status(self) -> ActivationStatus:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status is ActivationStatus.ACTIVE

    def activate(
        self,
        license: YomaLicense,
        *,
        now: datetime | None = None,
    ) -> ActivationResult:
        """Activate a valid license.

        Activation never creates execution authority.
        """

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        validation = LicenseValidator().validate(
            license,
            now=current,
        )

        if not validation.valid:
            return ActivationResult(
                license_id=license.license_id,
                organization_id=license.organization_id,
                status=self._status,
                changed=False,
                reason=f"activation_rejected:{validation.reason}",
                activated_at=self._activated_at,
            )

        if (
            self._status is ActivationStatus.ACTIVE
            and self._license_id == license.license_id
            and self._organization_id == license.organization_id
        ):
            return ActivationResult(
                license_id=license.license_id,
                organization_id=license.organization_id,
                status=self._status,
                changed=False,
                reason="already_active",
                activated_at=self._activated_at,
            )

        self._status = ActivationStatus.ACTIVE
        self._license_id = license.license_id
        self._organization_id = license.organization_id
        self._activated_at = current

        return ActivationResult(
            license_id=license.license_id,
            organization_id=license.organization_id,
            status=self._status,
            changed=True,
            reason="activation_successful",
            activated_at=self._activated_at,
        )

    def deactivate(
        self,
        *,
        now: datetime | None = None,
    ) -> ActivationResult:
        """Deactivate the current license."""

        if now is not None and now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        if self._status is not ActivationStatus.ACTIVE:
            return ActivationResult(
                license_id=self._license_id or "",
                organization_id=self._organization_id or "",
                status=self._status,
                changed=False,
                reason="already_inactive",
                activated_at=None,
            )

        if self._license_id is None or self._organization_id is None:
            return ActivationResult(
                license_id="",
                organization_id="",
                status=ActivationStatus.INACTIVE,
                changed=False,
                reason="already_inactive",
                activated_at=None,
            )

        license_id = self._license_id
        organization_id = self._organization_id

        self._status = ActivationStatus.DEACTIVATED
        self._activated_at = None

        return ActivationResult(
            license_id=license_id,
            organization_id=organization_id,
            status=self._status,
            changed=True,
            reason="deactivation_successful",
            activated_at=None,
        )

    def reset(self) -> None:
        """Reset activation state."""

        self._status = ActivationStatus.INACTIVE
        self._license_id = None
        self._organization_id = None
        self._activated_at = None
