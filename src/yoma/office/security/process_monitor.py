"""Defensive process anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProcessRisk(str, Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ProcessObservation:
    process_name: str
    pid: int | None = None
    parent_process: str | None = None
    expected: bool = True

    def __post_init__(self) -> None:
        if not self.process_name.strip():
            raise ValueError("process_name required")


@dataclass(frozen=True)
class ProcessAssessment:
    risk: ProcessRisk
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "risk": self.risk.value,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class ProcessMonitor:
    def assess(self, observation: ProcessObservation) -> ProcessAssessment:
        if not observation.expected:
            return ProcessAssessment(
                ProcessRisk.SUSPICIOUS,
                "unexpected process observed",
            )

        return ProcessAssessment(
            ProcessRisk.NORMAL,
            "process matches expected runtime observation",
        )
