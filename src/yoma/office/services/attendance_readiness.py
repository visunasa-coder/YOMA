from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AttendanceReadinessResult:
    """Read-only readiness assessment for an attendance integration."""

    installation_ready: bool
    attendance_detected: bool
    candidate_count: int
    adapter_available: bool
    configuration_required: bool
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.installation_ready, bool):
            raise TypeError("installation_ready must be a boolean")
        if not isinstance(self.attendance_detected, bool):
            raise TypeError("attendance_detected must be a boolean")
        if not isinstance(self.candidate_count, int):
            raise TypeError("candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("candidate_count must not be negative")
        if not isinstance(self.adapter_available, bool):
            raise TypeError("adapter_available must be a boolean")
        if not isinstance(self.configuration_required, bool):
            raise TypeError("configuration_required must be a boolean")
        if self.requires_human_approval is not True:
            raise ValueError(
                "attendance readiness must require human approval"
            )
        if self.executable is not False:
            raise ValueError(
                "attendance readiness must not be executable"
            )

    @property
    def ready(self) -> bool:
        return (
            self.installation_ready
            and self.attendance_detected
            and self.adapter_available
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "installation_ready": self.installation_ready,
            "attendance_detected": self.attendance_detected,
            "candidate_count": self.candidate_count,
            "adapter_available": self.adapter_available,
            "configuration_required": self.configuration_required,
            "requires_human_approval": True,
            "executable": False,
        }


class AttendanceReadiness:
    """Read-only attendance integration readiness evaluator."""

    def assess(
        self,
        *,
        deployment_ready: bool,
        assessment: Mapping[str, Any],
    ) -> AttendanceReadinessResult:
        if not isinstance(deployment_ready, bool):
            raise TypeError("deployment_ready must be a boolean")

        if not isinstance(assessment, Mapping):
            raise TypeError("assessment must be a mapping")

        candidate_count = assessment.get("candidate_count", 0)

        if not isinstance(candidate_count, int):
            raise TypeError(
                "assessment candidate_count must be an integer"
            )

        if candidate_count < 0:
            raise ValueError(
                "assessment candidate_count must not be negative"
            )

        candidates = assessment.get("candidates", ())

        if candidates is None:
            candidates = ()

        if not isinstance(candidates, (list, tuple)):
            raise TypeError(
                "assessment candidates must be a list or tuple"
            )

        attendance_detected = candidate_count > 0

        adapter_available = any(
            isinstance(candidate, Mapping)
            and candidate.get("adapter") == "generic_attendance"
            for candidate in candidates
        )

        return AttendanceReadinessResult(
            installation_ready=deployment_ready,
            attendance_detected=attendance_detected,
            candidate_count=candidate_count,
            adapter_available=adapter_available,
            configuration_required=attendance_detected,
        )
