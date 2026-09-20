"""Enterprise deployment package metadata for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class DeploymentComponent:
    """Immutable component included in a YOMA deployment."""

    name: str
    version: str
    component_type: str
    required: bool = True

    def __post_init__(self) -> None:
        for field_name in ("name", "version", "component_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "component_type": self.component_type,
            "required": self.required,
        }


@dataclass(frozen=True)
class DeploymentPackage:
    """Deterministic, secret-free description of a YOMA deployment package."""

    package_id: str
    version: str
    minimum_python_version: str
    components: tuple[DeploymentComponent, ...]
    manifest_version: str = "1"

    def __post_init__(self) -> None:
        for field_name in (
            "package_id",
            "version",
            "minimum_python_version",
            "manifest_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if not self.components:
            raise ValueError("deployment package must contain components")

    def manifest(self) -> dict[str, object]:
        """Return deterministic package metadata without secret material."""
        return {
            "manifest_version": self.manifest_version,
            "package_id": self.package_id,
            "version": self.version,
            "minimum_python_version": self.minimum_python_version,
            "components": [
                component.as_dict()
                for component in self.components
            ],
        }

    def manifest_bytes(self) -> bytes:
        """Return deterministic serialized manifest bytes."""
        import json

        return json.dumps(
            self.manifest(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def integrity_sha256(self) -> str:
        """Return the SHA-256 digest of the canonical manifest."""
        return sha256(self.manifest_bytes()).hexdigest()
