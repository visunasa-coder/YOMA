from __future__ import annotations

from typing import Iterable, Mapping, Any
from uuid import uuid4

from .incident_events import SecurityEvent, SecurityEventNormalizer
from .incident_correlation import SecurityEventCorrelator
from .incident_detection import IncidentDetector
from .incident_timeline import IncidentEvidenceTimeline
from .investigation import SecurityInvestigationEngine
from .response_advisor import IncidentResponseAdvisor
from .incident_workflow import IncidentApprovalWorkflow
from .incident_recovery import IncidentRecoveryManager
from .operations_dashboard import SecurityOperationsDashboard


class SecurityOperationsRuntime:
    """
    Defensive security operations intelligence.

    This runtime:
      - observes
      - normalizes
      - correlates
      - detects
      - investigates
      - recommends
      - creates approval workflows
      - assesses recovery

    It does NOT execute remediation.
    """

    def __init__(self) -> None:
        self.normalizer = SecurityEventNormalizer()
        self.correlator = SecurityEventCorrelator()
        self.detector = IncidentDetector()
        self.timeline = IncidentEvidenceTimeline()
        self.investigator = SecurityInvestigationEngine()
        self.advisor = IncidentResponseAdvisor()
        self.workflow_engine = IncidentApprovalWorkflow()
        self.recovery_manager = IncidentRecoveryManager()
        self.dashboard = SecurityOperationsDashboard()

    def analyze(
        self,
        events: Iterable[SecurityEvent | Mapping[str, Any]],
    ) -> dict[str, Any]:
        normalized = tuple(
            self.normalizer.normalize(e)
            for e in events
        )

        incident_id = uuid4().hex

        correlation = self.correlator.correlate(normalized)
        detection = self.detector.detect(normalized)
        timeline = self.timeline.build(normalized)

        investigation = self.investigator.investigate(
            incident_id=incident_id,
            events=normalized,
        )

        recommendations = self.advisor.recommend(detection)

        workflow = self.workflow_engine.create(
            incident_id=incident_id,
            recommendations=recommendations,
        )

        recovery = self.recovery_manager.assess(
            incident_id=incident_id,
            evidence_preserved=timeline.evidence_count > 0,
        )

        status = self.dashboard.build(
            events=normalized,
            detection=detection,
            evidence_count=timeline.evidence_count,
            recommendations_count=len(recommendations),
            workflow=workflow,
            recovery=recovery,
        )

        return {
            "incident_id": incident_id,
            "correlation": {
                "correlated": correlation.correlated,
                "score": correlation.score,
                "reason": correlation.reason,
                "event_ids": correlation.event_ids,
                "source_ids": correlation.source_ids,
            },
            "detection": {
                "detected": detection.detected,
                "severity": detection.severity.value,
                "confidence": detection.confidence,
                "reasons": detection.reasons,
                "event_ids": detection.event_ids,
            },
            "timeline": timeline.as_dict(),
            "investigation": {
                "incident_id": investigation.incident_id,
                "primary_sources": investigation.primary_sources,
                "affected_layers": investigation.affected_layers,
                "findings": investigation.findings,
                "evidence_event_ids": investigation.evidence_event_ids,
                "confidence": investigation.confidence,
                "read_only": investigation.read_only,
                "executable": investigation.executable,
            },
            "recommendations": [
                {
                    "action": r.action.value,
                    "reason": r.reason,
                    "priority": r.priority,
                    "requires_human_approval": r.requires_human_approval,
                    "executable": r.executable,
                }
                for r in recommendations
            ],
            "workflow": {
                "incident_id": workflow.incident_id,
                "approval_state": workflow.approval_state.value,
                "requires_human_approval": workflow.requires_human_approval,
                "executable": workflow.executable,
            },
            "recovery": {
                "incident_id": recovery.incident_id,
                "state": recovery.state.value,
                "evidence_preserved": recovery.evidence_preserved,
                "verification_required": recovery.verification_required,
                "post_incident_review_required": recovery.post_incident_review_required,
                "executable": recovery.executable,
            },
            "status": status.as_dict(),
            "requires_human_approval": True,
            "executable": False,
        }
