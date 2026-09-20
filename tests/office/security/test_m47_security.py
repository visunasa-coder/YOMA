from __future__ import annotations

import pytest

from yoma.office.security import (
    DatabaseGuard,
    FileGuard,
    RBAC,
    RateLimiter,
    RequestGuard,
    SecurityAuditChain,
    SecurityCore,
    SecurityDecision,
    SecurityIdentity,
    SecurityRole,
    SecurityRuntime,
    ThreatCategory,
    ThreatDetector,
    ThreatLevel,
    TrustLevel,
)


# ---------------- M47.2 Security Core ----------------

def test_core_denies_unauthenticated():
    r = SecurityCore().assess(
        authenticated=False,
        authorized=False,
    )
    assert r.decision is SecurityDecision.DENY
    assert r.executable is False


def test_core_denies_unauthorized():
    r = SecurityCore().assess(
        authenticated=True,
        authorized=False,
        trust_level=TrustLevel.TRUSTED,
    )
    assert r.decision is SecurityDecision.DENY


def test_core_denies_high_threat():
    r = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        threat_level=ThreatLevel.HIGH,
        approval_present=True,
    )
    assert r.decision is SecurityDecision.DENY


def test_core_requires_review_for_unknown_trust():
    r = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.UNKNOWN,
    )
    assert r.decision is SecurityDecision.REVIEW


def test_core_requires_approval():
    r = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
    )
    assert r.decision is SecurityDecision.REVIEW
    assert r.executable is False


def test_core_allow_never_becomes_execution_authority():
    r = SecurityCore().assess(
        authenticated=True,
        authorized=True,
        trust_level=TrustLevel.TRUSTED,
        approval_present=True,
    )
    assert r.decision is SecurityDecision.ALLOW
    assert r.requires_human_approval is True
    assert r.executable is False


# ---------------- M47.3 RBAC ----------------

def test_rbac_requires_authentication():
    rbac = RBAC({
        SecurityRole.ADMIN: {"database.read"},
    })

    identity = SecurityIdentity(
        "admin-1",
        SecurityRole.ADMIN,
        authenticated=False,
    )

    assert rbac.allowed(identity, "database.read") is False


def test_rbac_allows_explicit_permission():
    rbac = RBAC({
        SecurityRole.ADMIN: {"database.read"},
    })

    identity = SecurityIdentity(
        "admin-1",
        SecurityRole.ADMIN,
        authenticated=True,
    )

    assert rbac.allowed(identity, "database.read") is True
    assert rbac.allowed(identity, "database.write") is False


def test_rbac_unknown_permission_denied():
    rbac = RBAC({
        SecurityRole.OPERATOR: {"attendance.read"},
    })

    identity = SecurityIdentity(
        "operator-1",
        SecurityRole.OPERATOR,
        authenticated=True,
    )

    assert rbac.allowed(identity, "database.read") is False


# ---------------- M47.4 Request Defense ----------------

def test_request_guard_accepts_normal_request():
    result = RequestGuard().validate(
        body_size=100,
        text="hello YOMA",
    )
    assert result.valid is True


def test_request_guard_rejects_oversized_body():
    guard = RequestGuard(max_body_bytes=100)
    result = guard.validate(body_size=101)
    assert result.valid is False


def test_request_guard_rejects_control_characters():
    result = RequestGuard().validate(
        body_size=10,
        text="hello\x00world",
    )
    assert result.valid is False


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False


# ---------------- M47.5 Threat Detection ----------------

def test_threat_detector_normal():
    result = ThreatDetector().assess()
    assert result.level == "none"
    assert result.category is ThreatCategory.NONE


def test_threat_detector_auth_abuse():
    result = ThreatDetector().assess(
        failed_authentication_count=5,
    )
    assert result.level == "high"
    assert result.category is ThreatCategory.AUTHENTICATION_ABUSE


def test_threat_detector_privilege_anomaly():
    result = ThreatDetector().assess(
        privilege_anomaly=True,
    )
    assert result.level == "critical"


def test_threat_detector_data_access_anomaly():
    result = ThreatDetector().assess(
        abnormal_data_access=True,
    )
    assert result.level == "high"
    assert result.category is ThreatCategory.DATA_ACCESS_ANOMALY


def test_threat_detector_unknown_device():
    result = ThreatDetector().assess(
        unknown_device=True,
    )
    assert result.level == "medium"


def test_threat_detector_tampering():
    result = ThreatDetector().assess(
        configuration_tampering=True,
    )
    assert result.level == "critical"


# ---------------- M47.6 Audit ----------------

def test_audit_chain_verifies():
    chain = SecurityAuditChain()

    first = chain.record(
        event_type="login",
        actor="user",
        resource="control-server",
        status="success",
    )

    second = chain.record(
        event_type="request",
        actor="user",
        resource="attendance",
        status="review",
    )

    assert first.previous_hash == "GENESIS"
    assert second.previous_hash == first.event_hash
    assert chain.verify() is True


def test_audit_removes_sensitive_metadata():
    chain = SecurityAuditChain()

    event = chain.record(
        event_type="auth",
        actor="user",
        resource="api",
        status="success",
        metadata={
            "token": "secret-token",
            "password": "secret-password",
            "safe_value": "kept",
        },
    )

    assert "token" not in event.metadata
    assert "password" not in event.metadata
    assert event.metadata["safe_value"] == "kept"


def test_audit_detects_tampering():
    chain = SecurityAuditChain()

    chain.record(
        event_type="test",
        actor="user",
        resource="security",
        status="ok",
    )

    chain.record(
        event_type="test2",
        actor="user",
        resource="security",
        status="ok",
    )

    chain._events[0] = chain._events[0].__class__(
        **{
            **chain._events[0].as_dict(),
            "status": "tampered",
        }
    )

    assert chain.verify() is False


# ---------------- M47.7 File / Database ----------------

def test_file_guard_accepts_allowed_file():
    result = FileGuard().inspect(
        filename="attendance.csv",
        size_bytes=1024,
    )
    assert result.allowed is True


def test_file_guard_rejects_unknown_extension():
    result = FileGuard().inspect(
        filename="payload.exe",
        size_bytes=1024,
    )
    assert result.allowed is False


def test_file_guard_rejects_large_file():
    result = FileGuard(max_size_bytes=100).inspect(
        filename="data.csv",
        size_bytes=101,
    )
    assert result.allowed is False


def test_database_guard_requires_scope():
    result = DatabaseGuard().inspect(
        operation="read",
        scope="",
    )
    assert result.allowed is False


def test_database_guard_allows_scoped_read():
    result = DatabaseGuard().inspect(
        operation="read",
        scope="attendance.events",
    )
    assert result.allowed is True


def test_database_guard_blocks_unapproved_write():
    result = DatabaseGuard().inspect(
        operation="write",
        scope="attendance.events",
        approved=False,
    )
    assert result.allowed is False


def test_database_guard_blocks_dangerous_sql():
    result = DatabaseGuard().inspect_sql(
        "DROP TABLE employees"
    )
    assert result.allowed is False


def test_database_guard_accepts_read_sql_pattern():
    result = DatabaseGuard().inspect_sql(
        "SELECT employee_id FROM attendance WHERE employee_id = ?"
    )
    assert result.allowed is True


# ---------------- M47.8 Runtime ----------------

def test_security_runtime_status():
    runtime = SecurityRuntime()
    status = runtime.status()

    assert status["security"] == "active"
    assert status["fail_closed"] is True
    assert status["authentication_required"] is True
    assert status["authorization_required"] is True
    assert status["threat_detection"] is True
    assert status["database_guard"] is True
    assert status["audit_chain"] is True
    assert status["audit_chain_valid"] is True
    assert status["requires_human_approval"] is True
    assert status["executable"] is False


def test_security_runtime_assessment_is_audited():
    runtime = SecurityRuntime()

    result = runtime.assess(
        authenticated=False,
        authorized=False,
    )

    assert result.decision is SecurityDecision.DENY
    assert len(runtime.audit.list()) == 1
    assert runtime.audit.verify() is True


def test_security_runtime_threat_is_audited():
    runtime = SecurityRuntime()

    result = runtime.threat_assess(
        failed_authentication_count=5,
    )

    assert result.level == "high"
    assert len(runtime.audit.list()) == 1
    assert runtime.audit.verify() is True


# ---------------- Global invariant ----------------

@pytest.mark.parametrize(
    "assessment",
    [
        SecurityCore().assess(
            authenticated=True,
            authorized=True,
            trust_level=TrustLevel.TRUSTED,
            approval_present=True,
        ),
    ],
)
def test_security_can_never_claim_execution_authority(assessment):
    assert assessment.executable is False
    assert assessment.requires_human_approval is True
