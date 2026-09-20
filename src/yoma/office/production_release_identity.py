"""YOMA v1.0 production release identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProductionReleaseIdentity:
    product_name: str = "YOMA"
    version: str = "1.0.0"
    release_name: str = "YOMA v1.0"
    release_channel: str = "production"
    vendor_name: str = "VP Technologies"
    release_status: str = "candidate"

    def __post_init__(self) -> None:
        for name, value in (
            ("product_name", self.product_name),
            ("version", self.version),
            ("release_name", self.release_name),
            ("release_channel", self.release_channel),
            ("vendor_name", self.vendor_name),
            ("release_status", self.release_status),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_name": self.product_name,
            "version": self.version,
            "release_name": self.release_name,
            "release_channel": self.release_channel,
            "vendor_name": self.vendor_name,
            "release_status": self.release_status,
        }

    @property
    def is_v1(self) -> bool:
        return self.version == "1.0.0"

    @property
    def is_production(self) -> bool:
        return self.release_channel == "production"


class ProductionReleaseIdentityValidator:
    """Read-only validation of the YOMA production release identity."""

    def validate(
        self,
        identity: ProductionReleaseIdentity,
    ) -> bool:
        return (
            identity.is_v1
            and identity.is_production
            and identity.product_name == "YOMA"
            and identity.vendor_name == "VP Technologies"
            and identity.release_status == "candidate"
        )
