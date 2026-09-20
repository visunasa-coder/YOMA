"""Canonical licensing models for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping


class LicenseStatus(str, Enum):
    """Lifecycle status of a YOMA license."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class ProductEdition(str, Enum):
    """YOMA product editions."""

    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class YomaLicense:
    """Immutable canonical representation of a YOMA license."""

    license_id: str
    organization_id: str
    edition: ProductEdition
    status: LicenseStatus
    issued_at: datetime
    expires_at: datetime | None = None
    entitlements: Mapping[str, bool] = None

    def __post_init__(self) -> None:
        if not self.license_id.strip():
            raise ValueError("license_id must not be empty")

        if not self.organization_id.strip():
            raise ValueError("organization_id must not be empty")

        if self.issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")

        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")

        if (
            self.expires_at is not None
            and self.expires_at < self.issued_at
        ):
            raise ValueError("expires_at must not precede issued_at")

        object.__setattr__(
            self,
            "entitlements",
            dict(self.entitlements or {}),
        )

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """Return whether the license has passed its expiration time."""

        if self.expires_at is None:
            return False

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        return current >= self.expires_at

    def is_valid_lifecycle(self) -> bool:
        """Return whether the license lifecycle status permits normal use."""

        return self.status is LicenseStatus.ACTIVE

    def has_entitlement(self, capability: str) -> bool:
        """Return whether a capability is explicitly entitled."""

        if not capability.strip():
            raise ValueError("capability must not be empty")

        return bool(self.entitlements.get(capability, False))
