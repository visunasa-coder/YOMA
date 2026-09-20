"""Commercial release manifest and integrity for YOMA."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ReleaseComponent:
    name: str
    version: str
    component_type: str
    required: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("name", self.name),
            ("version", self.version),
            ("component_type", self.component_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "component_type": self.component_type,
            "required": self.required,
        }


@dataclass(frozen=True)
class ReleaseManifest:
    product_name: str
    product_version: str
    release_channel: str
    vendor_name: str
    components: tuple[ReleaseComponent, ...]
    manifest_version: str = "1"

    def __post_init__(self) -> None:
        for name, value in (
            ("product_name", self.product_name),
            ("product_version", self.product_version),
            ("release_channel", self.release_channel),
            ("vendor_name", self.vendor_name),
            ("manifest_version", self.manifest_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if not isinstance(self.components, tuple):
            raise TypeError("components must be a tuple")

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "product_name": self.product_name,
            "product_version": self.product_version,
            "release_channel": self.release_channel,
            "vendor_name": self.vendor_name,
            "components": [
                component.as_dict()
                for component in self.components
            ],
        }

    def manifest_bytes(self) -> bytes:
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def integrity_sha256(self) -> str:
        return hashlib.sha256(self.manifest_bytes()).hexdigest()

    def contains_secret_fields(self) -> bool:
        secret_terms = (
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "private_key",
            "credential",
        )

        def contains_secret(value: Any) -> bool:
            if isinstance(value, Mapping):
                return any(
                    any(term in str(key).lower() for term in secret_terms)
                    or contains_secret(item)
                    for key, item in value.items()
                )
            if isinstance(value, (list, tuple)):
                return any(contains_secret(item) for item in value)
            return any(
                term in str(value).lower()
                for term in secret_terms
            )

        return contains_secret(self.as_dict())
