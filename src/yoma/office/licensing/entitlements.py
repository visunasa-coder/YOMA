"""License entitlement resolution for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .license_model import ProductEdition, YomaLicense


@dataclass(frozen=True)
class EntitlementResult:
    """Immutable result of an entitlement lookup."""

    capability: str
    entitled: bool
    edition: ProductEdition
    reason: str


class LicenseEntitlementResolver:
    """Resolve licensed capabilities without granting execution authority."""

    def resolve(
        self,
        license: YomaLicense,
        capability: str,
    ) -> EntitlementResult:
        if not isinstance(license, YomaLicense):
            raise TypeError("license must be a YomaLicense")

        if not capability.strip():
            raise ValueError("capability must not be empty")

        entitled = license.has_entitlement(capability)

        return EntitlementResult(
            capability=capability,
            entitled=entitled,
            edition=license.edition,
            reason=(
                "capability_entitled"
                if entitled
                else "capability_not_entitled"
            ),
        )

    def resolve_many(
        self,
        license: YomaLicense,
        capabilities: list[str] | tuple[str, ...],
    ) -> tuple[EntitlementResult, ...]:
        """Resolve multiple capabilities deterministically."""

        if not isinstance(license, YomaLicense):
            raise TypeError("license must be a YomaLicense")

        return tuple(
            self.resolve(license, capability)
            for capability in capabilities
        )

    def entitled_capabilities(
        self,
        license: YomaLicense,
    ) -> tuple[str, ...]:
        """Return explicitly entitled capabilities in deterministic order."""

        if not isinstance(license, YomaLicense):
            raise TypeError("license must be a YomaLicense")

        return tuple(
            sorted(
                capability
                for capability, entitled in license.entitlements.items()
                if entitled
            )
        )
