"""Defensive filesystem observation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FileEventRisk(str, Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    CRITICAL = "critical"


@dataclass(frozen=True)
class FileSystemObservation:
    path: str
    actor: str
    operation: str
    approved_actor: bool = False
    approved_path: bool = False


@dataclass(frozen=True)
class FileSystemAssessment:
    risk: FileEventRisk
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


class FileSystemMonitor:
    def assess(
        self,
        observation: FileSystemObservation,
    ) -> FileSystemAssessment:

        if not observation.approved_actor:
            return FileSystemAssessment(
                FileEventRisk.HIGH if False else FileEventRisk.SUSPICIOUS,
                "unapproved actor accessed monitored path",
            )

        if not observation.approved_path:
            return FileSystemAssessment(
                FileEventRisk.SUSPICIOUS,
                "actor accessed path outside approved scope",
            )

        return FileSystemAssessment(
            FileEventRisk.NORMAL,
            "filesystem observation matches approved scope",
        )
