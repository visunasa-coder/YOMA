from __future__ import annotations

from typing import Any, Mapping


class AttendanceAdapterCandidatePlanner:
    """
    Converts safe attendance-environment observations into
    adapter configuration candidates.

    This planner does NOT probe, connect, authenticate, configure,
    activate, or modify any device.
    """

    ADAPTER_NAME = "generic_attendance"
    CATEGORY = "attendance"

    @staticmethod
    def _clean(value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            return value if value else None

        return value

    def plan(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, Mapping):
            raise TypeError("candidate must be a mapping")

        if candidate.get("category") != self.CATEGORY:
            raise ValueError("candidate is not an attendance candidate")

        transport = self._clean(candidate.get("transport"))

        if not transport:
            raise ValueError("attendance candidate transport is required")

        device: dict[str, Any] = {}

        for field in (
            "port",
            "name",
            "description",
            "manufacturer",
            "vid",
            "pid",
            "device_class",
            "status",
            "instance_id",
        ):
            value = self._clean(candidate.get(field))
            if value is not None:
                device[field] = value

        config = {
            "adapter": self.ADAPTER_NAME,
            "category": self.CATEGORY,
            "transport": transport,
            "device": device,
        }

        return {
            "adapter": self.ADAPTER_NAME,
            "category": self.CATEGORY,
            "candidate": config,
            "confidence": self._clean(candidate.get("confidence"))
            or "possible",
            "source": self._clean(candidate.get("source"))
            or "local_environment",
            "requires_human_approval": True,
            "executable": False,
            "activation_allowed": False,
        }

    def plan_all(
        self,
        candidates: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if not isinstance(candidates, list):
            raise TypeError("candidates must be a list")

        return [self.plan(candidate) for candidate in candidates]
