from yoma.office.security.m49 import (
    IncidentApprovalWorkflow,
    IncidentDetector,
    IncidentResponseAdvisor,
    SecurityEvent,
    SecurityEventType,
    IncidentSeverity,
    SecurityOperationsRuntime,
    SecurityEventCorrelator,
    IncidentEvidenceTimeline,
    SecurityInvestigationEngine,
    IncidentRecoveryManager,
    ResponseApprovalState,
)


def event(kind, severity="high", source="host", source_id="source-1"):
    return SecurityEvent.create(
        event_type=SecurityEventType(kind),
        severity=IncidentSeverity(severity),
        source=source,
        source_id=source_id,
        description=kind,
    )


def test_m49_1_normalization():
    e = event("authentication_failure", "low")
    assert e.event_id
    assert e.event_type == SecurityEventType.AUTHENTICATION_FAILURE
    assert e.as_dict()["source_id"] == "source-1"


def test_m49_2_correlation():
    events = (
        event("authentication_failure", "low"),
        event("privilege_attempt", "high"),
    )
    result = SecurityEventCorrelator().correlate(events)
    assert result.correlated is True
    assert result.score >= 30


def test_m49_3_detection():
    result = IncidentDetector().detect(
        (event("configuration_tamper", "high"),)
    )
    assert result.detected is True
    assert result.severity == IncidentSeverity.HIGH


def test_m49_3_critical_detection():
    result = IncidentDetector().detect(
        (event("integrity_failure", "critical"),)
    )
    assert result.severity == IncidentSeverity.CRITICAL


def test_m49_4_timeline():
    events = (
        event("authentication_failure", "low"),
        event("configuration_tamper", "high"),
    )
    timeline = IncidentEvidenceTimeline().build(events)
    assert timeline.evidence_count == 2
    assert timeline.chronologically_ordered is True


def test_m49_5_investigation_is_read_only():
    events = (event("privilege_attempt", "high"),)
    result = SecurityInvestigationEngine().investigate(
        incident_id="incident-1",
        events=events,
    )
    assert result.read_only is True
    assert result.executable is False


def test_m49_6_response_recommendations():
    detection = IncidentDetector().detect(
        (event("configuration_tamper", "high"),)
    )
    recommendations = IncidentResponseAdvisor().recommend(detection)
    assert recommendations
    assert all(r.requires_human_approval for r in recommendations)
    assert all(not r.executable for r in recommendations)


def test_m49_7_workflow_requires_approval():
    detection = IncidentDetector().detect(
        (event("privilege_attempt", "high"),)
    )
    recommendations = IncidentResponseAdvisor().recommend(detection)
    workflow = IncidentApprovalWorkflow().create(
        incident_id="incident-1",
        recommendations=recommendations,
    )
    assert workflow.approval_state == ResponseApprovalState.PENDING
    assert workflow.requires_human_approval is True
    assert workflow.executable is False


def test_m49_7_approval_does_not_execute():
    detection = IncidentDetector().detect(
        (event("privilege_attempt", "high"),)
    )
    recommendations = IncidentResponseAdvisor().recommend(detection)
    engine = IncidentApprovalWorkflow()
    workflow = engine.create(
        incident_id="incident-1",
        recommendations=recommendations,
    )
    approved = engine.approve(workflow)
    assert approved.approval_state == ResponseApprovalState.APPROVED
    assert approved.executable is False


def test_m49_8_recovery_requires_verification():
    assessment = IncidentRecoveryManager().assess(
        incident_id="incident-1",
        evidence_preserved=True,
    )
    assert assessment.verification_required is True
    assert assessment.executable is False


def test_m49_9_dashboard_is_defensive():
    result = SecurityOperationsRuntime().analyze(
        [
            event("authentication_failure", "low"),
            event("privilege_attempt", "high"),
            event("configuration_tamper", "high"),
        ]
    )
    status = result["status"]
    assert status["active"] is True
    assert status["incident_detected"] is True
    assert status["requires_human_approval"] is True
    assert status["executable"] is False


def test_m49_10_unified_runtime():
    result = SecurityOperationsRuntime().analyze(
        [
            event("authentication_failure", "low"),
            event("privilege_attempt", "high"),
            event("configuration_tamper", "high"),
            event("suspicious_file", "medium"),
        ]
    )

    assert result["incident_id"]
    assert result["correlation"]["correlated"] is True
    assert result["detection"]["detected"] is True
    assert result["timeline"]["evidence_count"] == 4
    assert result["investigation"]["read_only"] is True
    assert result["investigation"]["executable"] is False
    assert result["recommendations"]
    assert result["workflow"]["approval_state"] == "pending"
    assert result["workflow"]["requires_human_approval"] is True
    assert result["workflow"]["executable"] is False
    assert result["recovery"]["verification_required"] is True
    assert result["executable"] is False


def test_m49_10_no_events_is_safe():
    result = SecurityOperationsRuntime().analyze([])
    assert result["detection"]["detected"] is False
    assert result["recommendations"] == []
    assert result["executable"] is False


def test_m49_10_runtime_never_creates_execution_authority():
    result = SecurityOperationsRuntime().analyze(
        [event("integrity_failure", "critical")]
    )
    assert result["requires_human_approval"] is True
    assert result["executable"] is False
    assert result["workflow"]["executable"] is False
    assert result["investigation"]["executable"] is False
