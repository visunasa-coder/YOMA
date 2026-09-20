from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .incident_events import IncidentSeverity
from .incident_detection import IncidentDetection


class ResponseAction(str, Enum):
    REVIEW_SOURCE = "review_source"
    REVIEW_CREDENTIALS = "review_credentials"
    REVIEW_PROCESSES = "review_processes"
    REVIEW_CONFIGURATION = "review_configuration"
    TEMPORARY_SOURCE_ISOLATION = "temporary_source_isolation"
    PRESERVE_EVIDENCE = "preserve_evidence"
    RECOVERY_REVIEW = "recovery_review"


@dataclass(frozen=True)
class ResponseRecommendation:
    action: ResponseAction
    reason: str
    priority: int
    requires_human_approval: bool = True
    executable: bool = False


class IncidentResponseAdvisor:
    def recommend(
        self,
        detection: IncidentDetection,
    ) -> tuple[ResponseRecommendation, ...]:
        if not detection.detected:
            return ()

        recommendations = [
            ResponseRecommendation(
                ResponseAction.PRESERVE_EVIDENCE,
                "preserve the incident evidence before remediation",
                1,
            ),
            ResponseRecommendation(
                ResponseAction.REVIEW_SOURCE,
                "review the source associated with the incident",
                2,
            ),
        ]

        if detection.severity in (
            IncidentSeverity.HIGH,
            IncidentSeverity.CRITICAL,
        ):
            recommendations.extend([
                ResponseRecommendation(
                    ResponseAction.REVIEW_CREDENTIALS,
                    "review potentially exposed credentials",
                    3,
                ),
                ResponseRecommendation(
                    ResponseAction.REVIEW_CONFIGURATION,
                    "review affected security configuration",
                    4,
                ),
                ResponseRecommendation(
                    ResponseAction.TEMPORARY_SOURCE_ISOLATION,
                    "consider temporary isolation of the suspicious source",
                    5,
                ),
            ])

        if detection.severity == IncidentSeverity.CRITICAL:
            recommendations.append(
                ResponseRecommendation(
                    ResponseAction.RECOVERY_REVIEW,
                    "critical incident requires recovery assessment",
                    6,
                )
            )

        return tuple(recommendations)
