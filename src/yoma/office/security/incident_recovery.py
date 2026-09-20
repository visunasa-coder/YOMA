from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecoveryState(str, Enum):
    NONE = "none"
    ASSESSMENT = "assessment"
    RECOVERY_REVIEW = "recovery_review"
    RECOVERING = "recovering"
    RECOVERED = "recovered"


@dataclass(frozen=True)
class RecoveryAssessment:
    incident_id: str
    state: RecoveryState
    evidence_preserved: bool
    verification_required: bool
    post_incident_review_required: bool
    executable: bool = False


class IncidentRecoveryManager:
    def assess(
        self,
        *,
        incident_id: str,
        evidence_preserved: bool,
    ) -> RecoveryAssessment:
        return RecoveryAssessment(
            incident_id=incident_id,
            state=RecoveryState.ASSESSMENT,
            evidence_preserved=evidence_preserved,
            verification_required=True,
            post_incident_review_required=True,
            executable=False,
        )

    def mark_recovered(
        self,
        assessment: RecoveryAssessment,
    ) -> RecoveryAssessment:
        return RecoveryAssessment(
            incident_id=assessment.incident_id,
            state=RecoveryState.RECOVERED,
            evidence_preserved=assessment.evidence_preserved,
            verification_required=False,
            post_incident_review_required=True,
            executable=False,
        )
