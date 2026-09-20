"""Enterprise Windows service integration metadata for YOMA."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowsServiceConfiguration:
    """Immutable Windows service registration configuration."""

    service_name: str = "YomaControlServer"
    display_name: str = "YOMA Control Server"
    description: str = (
        "Runs the YOMA Office Management Control Server in the background."
    )
    start_type: str = "auto"

    def __post_init__(self) -> None:
        for field_name in (
            "service_name",
            "display_name",
            "description",
            "start_type",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if self.start_type not in {"auto", "manual", "disabled"}:
            raise ValueError("start_type is invalid")

    def as_dict(self) -> dict[str, str]:
        return {
            "service_name": self.service_name,
            "display_name": self.display_name,
            "description": self.description,
            "start_type": self.start_type,
        }
