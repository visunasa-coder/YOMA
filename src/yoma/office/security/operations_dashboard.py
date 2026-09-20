from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .incident_events import IncidentSeverity, SecurityEvent
from .incident_detection import IncidentDetection
from .incident_workflow import IncidentResponseWorkflow
from .incident_recovery import RecoveryAssessment


@dataclass(frozen=True)
class SecurityOperationsStatus:
    active: bool
    total_events: int
    incident_detected: bool
    severity: IncidentSeverity
    confidence: float
    evidence_count: int
    recommendations_count: int
    approval_pending: bool
    contained: bool
    recovery_state: str
    requires_human_approval: bool
    executable: bool

    def as_dict(self) -> dict:
        return {
            "active": self.active,
            "total_events": self.total_events,
            "incident_detected": self.incident_detected,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "recommendations_count": self.recommendations_count,
            "approval_pending": self.approval_pending,
            "contained": self.contained,
            "recovery_state": self.recovery_state,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class SecurityOperationsDashboard:
    def build(
        self,
        *,
        events: Iterable[SecurityEvent],
        detection: IncidentDetection,
        evidence_count: int,
        recommendations_count: int,
        workflow: IncidentResponseWorkflow,
        recovery: RecoveryAssessment,
        contained: bool = False,
    ) -> SecurityOperationsStatus:
        items = tuple(events)

        return SecurityOperationsStatus(
            active=True,
            total_events=len(items),
            incident_detected=detection.detected,
            severity=detection.severity,
            confidence=detection.confidence,
            evidence_count=evidence_count,
            recommendations_count=recommendations_count,
            approval_pending=(
                workflow.approval_state.value == "pending"
            ),
            contained=contained,
            recovery_state=recovery.state.value,
            requires_human_approval=True,
            executable=False,
        )
