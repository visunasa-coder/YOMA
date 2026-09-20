import time

from yoma.office.security.identity import (
    EnterpriseIdentity,
    IdentityRegistry,
    IdentityType,
    TrustState,
)
from yoma.office.security.authentication import (
    AuthenticationBoundary,
    AuthenticationDecision,
)
from yoma.office.security.permissions import PermissionGovernance
from yoma.office.security.device_trust import (
    DeviceTrustEngine,
    DevicePosture,
)
from yoma.office.security.session_security import (
    SessionSecurity,
    SecuritySession,
)
from yoma.office.security.privileged_access import (
    PrivilegedAccessGovernance,
    PrivilegeRequest,
    PrivilegeDecision,
)
from yoma.office.security.service_identity import (
    ServiceIdentityGovernance,
    ServiceIdentity,
)
from yoma.office.security.zero_trust import (
    ZeroTrustAccessEngine,
    ZeroTrustContext,
    ZeroTrustDecision,
)
from yoma.office.security.access_audit import (
    AccessAuditChain,
    AccessAuditEvent,
)
from yoma.office.security.identity_runtime import (
    IdentityGovernanceRuntime,
    IdentityGovernanceRequest,
)


def test_m51_1_identity_model():
    registry = IdentityRegistry()
    identity = EnterpriseIdentity(
        "u1",
        IdentityType.HUMAN,
        "employee",
        frozenset({"EMPLOYEE"}),
        frozenset({"office.read"}),
        TrustState.TRUSTED,
        True,
    )
    registry.register(identity)
    assert registry.get("u1") == identity


def test_m51_1_revoke():
    registry = IdentityRegistry()
    identity = EnterpriseIdentity(
        "u2",
        IdentityType.HUMAN,
        "employee",
        authenticated=True,
        trust=TrustState.TRUSTED,
    )
    registry.register(identity)
    assert registry.revoke("u2") is True
    assert registry.get("u2").active is False


def test_m51_2_authentication_denied():
    result = AuthenticationBoundary().authenticate("u1", False)
    assert result.decision == AuthenticationDecision.DENIED
    assert result.executable is False


def test_m51_2_reauthentication():
    result = AuthenticationBoundary().authenticate(
        "u1",
        True,
        session_valid=False,
    )
    assert result.decision == AuthenticationDecision.REAUTH_REQUIRED


def test_m51_3_permission_denied():
    result = PermissionGovernance().evaluate(
        "office.write",
        frozenset({"office.read"}),
    )
    assert result.decision.value == "deny"


def test_m51_3_protected_permission_requires_approval():
    result = PermissionGovernance().evaluate(
        "office.read",
        frozenset({"office.read"}),
    )
    assert result.decision.value == "review"

def test_m51_4_unknown_device_denied():
    result = DeviceTrustEngine().assess(
        DevicePosture("d1", True, True, True, False)
    )
    assert result.decision.value == "denied"


def test_m51_4_trusted_device():
    result = DeviceTrustEngine().assess(
        DevicePosture("d1", True, True, True, True)
    )
    assert result.decision.value == "trusted"


def test_m51_5_expired_session():
    result = SessionSecurity().evaluate(
        SecuritySession("s1", "u1", 0, 1),
        now=10,
    )
    assert result.decision.value == "expired"
    assert result.reauthentication_required is True


def test_m51_6_privilege_requires_approval():
    result = PrivilegedAccessGovernance().evaluate(
        PrivilegeRequest(
            "u1",
            "ADMIN",
            "server",
            "maintenance",
            approved=False,
        )
    )
    assert result.decision == PrivilegeDecision.REVIEW
    assert result.elevated is False


def test_m51_6_privilege_approved():
    result = PrivilegedAccessGovernance().evaluate(
        PrivilegeRequest(
            "u1",
            "ADMIN",
            "server",
            "maintenance",
            approved=True,
        )
    )
    assert result.decision == PrivilegeDecision.ALLOW


def test_m51_7_service_scope():
    result = ServiceIdentityGovernance().evaluate(
        ServiceIdentity("svc1", "google", frozenset({"gmail.read"})),
        "gmail.send",
        approved=True,
    )
    assert result.allowed is False


def test_m51_8_zero_trust_denies_unauthenticated():
    result = ZeroTrustAccessEngine().decide(
        ZeroTrustContext(
            authenticated=False,
            authorized=True,
            trusted_device=True,
            active_session=True,
            threat_level="none",
            resource="db",
            approved=True,
        )
    )
    assert result.decision == ZeroTrustDecision.DENY


def test_m51_8_zero_trust_requires_approval():
    result = ZeroTrustAccessEngine().decide(
        ZeroTrustContext(
            authenticated=True,
            authorized=True,
            trusted_device=True,
            active_session=True,
            threat_level="none",
            resource="db",
            approved=False,
        )
    )
    assert result.decision == ZeroTrustDecision.REVIEW


def test_m51_8_zero_trust_critical_threat_denied():
    result = ZeroTrustAccessEngine().decide(
        ZeroTrustContext(
            authenticated=True,
            authorized=True,
            trusted_device=True,
            active_session=True,
            threat_level="critical",
            resource="db",
            approved=True,
        )
    )
    assert result.decision == ZeroTrustDecision.DENY


def test_m51_9_audit_chain():
    chain = AccessAuditChain()
    chain.append(
        AccessAuditEvent(
            "e1", "u1", "db", "deny", "test", time.time()
        )
    )
    chain.append(
        AccessAuditEvent(
            "e2", "u1", "file", "deny", "test", time.time()
        )
    )
    assert chain.verify() is True
    assert len(chain.events) == 2


def test_m51_10_unified_runtime_fail_closed():
    runtime = IdentityGovernanceRuntime()

    identity = EnterpriseIdentity(
        "u1",
        IdentityType.HUMAN,
        "employee",
        frozenset({"EMPLOYEE"}),
        frozenset({"office.read"}),
        TrustState.TRUSTED,
        True,
    )
    runtime.identities.register(identity)

    result = runtime.evaluate(
        IdentityGovernanceRequest(
            identity_id="u1",
            permission="office.read",
            resource="office-db",
            device_id="device-1",
            threat_level="none",
            approved=False,
        )
    )

    assert result["decision"] == "review"
    assert result["requires_human_approval"] is True
    assert result["executable"] is False
    assert result["audit_chain_valid"] is True


def test_m51_10_approved_access_still_has_no_execution_authority():
    runtime = IdentityGovernanceRuntime()

    identity = EnterpriseIdentity(
        "u2",
        IdentityType.HUMAN,
        "manager",
        frozenset({"MANAGER"}),
        frozenset({"office.read"}),
        TrustState.TRUSTED,
        True,
    )
    runtime.identities.register(identity)

    result = runtime.evaluate(
        IdentityGovernanceRequest(
            identity_id="u2",
            permission="office.read",
            resource="office-db",
            device_id="device-2",
            threat_level="none",
            approved=True,
        )
    )

    assert result["decision"] == "allow"
    assert result["requires_human_approval"] is True
    assert result["executable"] is False


def test_m51_status():
    status = IdentityGovernanceRuntime().status()

    assert status["active"] is True
    assert status["identity_model"] is True
    assert status["authentication_boundary"] is True
    assert status["rbac"] is True
    assert status["least_privilege"] is True
    assert status["device_trust"] is True
    assert status["session_security"] is True
    assert status["privileged_access_governance"] is True
    assert status["service_identity_governance"] is True
    assert status["zero_trust"] is True
    assert status["access_audit"] is True
    assert status["anomaly_detection"] is True
    assert status["fail_closed"] is True
    assert status["requires_human_approval"] is True
    assert status["executable"] is False
