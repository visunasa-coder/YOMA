"""Commercial product and edition metadata for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProductMetadata:
    product_name: str = "YOMA"
    product_version: str = "1.0.0"
    release_channel: str = "commercial"
    vendor_name: str = "VP Technologies"
    product_description: str = (
        "AI-powered governed workplace intelligence and automation platform."
    )

    def __post_init__(self) -> None:
        for name, value in (
            ("product_name", self.product_name),
            ("product_version", self.product_version),
            ("release_channel", self.release_channel),
            ("vendor_name", self.vendor_name),
            ("product_description", self.product_description),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_name": self.product_name,
            "product_version": self.product_version,
            "release_channel": self.release_channel,
            "vendor_name": self.vendor_name,
            "product_description": self.product_description,
        }


@dataclass(frozen=True)
class CommercialEdition:
    edition_id: str
    display_name: str
    target_market: str
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("edition_id", self.edition_id),
            ("display_name", self.display_name),
            ("target_market", self.target_market),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if not isinstance(self.capabilities, tuple):
            raise TypeError("capabilities must be a tuple")

    def as_dict(self) -> dict[str, Any]:
        return {
            "edition_id": self.edition_id,
            "display_name": self.display_name,
            "target_market": self.target_market,
            "capabilities": list(self.capabilities),
        }


class CommercialProductCatalog:
    """Deterministic, non-executable commercial product catalog."""

    def __init__(
        self,
        *,
        product: ProductMetadata | None = None,
        editions: tuple[CommercialEdition, ...] = (),
    ) -> None:
        self.product = product or ProductMetadata()
        self.editions = editions

    def catalog(self) -> dict[str, Any]:
        return {
            "product": self.product.as_dict(),
            "editions": [
                edition.as_dict()
                for edition in self.editions
            ],
        }

    def get_edition(self, edition_id: str) -> CommercialEdition | None:
        for edition in self.editions:
            if edition.edition_id == edition_id:
                return edition
        return None
