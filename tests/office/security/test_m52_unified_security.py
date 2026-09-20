from yoma.office.security import (
    SecurityEnforcementDecision,
    UnifiedSecurityPolicyPlane,
    SecurityLayerState,
    CrossLayerSecurityEnforcer,
    FinalSecurityEnforcementBoundary,
    SecurityContext,
    SecurityStatePropagator,
    EnterpriseIntegrationSecurity,
    SecurityFailSafe,
    SecurityFailSafeState,
    UnifiedSecurityRuntime,
)


def test_m52_1_policy_plane_fail_closed():
    result = UnifiedSecurityPolicyPlane().evaluate(
        request_valid=False,
        identity_allowed=True,
        host_safe=True,
        threat_safe=True,
        data_allowed=True,
        governance_allowed=True,
    )
    assert result.decision is SecurityEnforcementDecision.DENY
    assert result.executable is False


def test_m52_2_cross_layer():
    result = CrossLayerSecurityEnforcer().enforce(
        SecurityLayerState(
            request_valid=True,
            identity_allowed=True,
            host_safe=True,
            threat_safe=True,
            data_allowed=True,
            governance_allowed=True,
            review_required=True,
        )
    )
    assert result.decision is SecurityEnforcementDecision.REVIEW


def test_m52_3_host_precedence():
    assert (
        SecurityContext(
            actor_id="u1",
            identity_trusted=True,
            device_trusted=True,
            session_valid=True,
            request_id="r1",
            source_id="s1",
        ).can_continue()
    )


def test_m52_4_context_propagation():
    context = SecurityContext(
        actor_id="u1",
        identity_trusted=True,
        device_trusted=True,
        session_valid=True,
        request_id="r1",
        source_id="s1",
    )
    assert context.as_dict()["request_id"] == "r1"


def test_m52_5_final_boundary_never_authorizes_execution():
    decision = UnifiedSecurityPolicyPlane().evaluate(
        request_valid=True,
        identity_allowed=True,
        host_safe=True,
        threat_safe=True,
        data_allowed=True,
        governance_allowed=True,
        approval_present=True,
    )
    result = FinalSecurityEnforcementBoundary().evaluate(
        decision,
        governed_authorization=True,
    )
    assert result.execution_authorized is False


def test_m52_6_restricted_state():
    state = SecurityStatePropagator().derive(
        host_state="compromised"
    )
    assert state.restricted is True
    assert state.host_restricted is True


def test_m52_7_integrations():
    engine = EnterpriseIntegrationSecurity()
    result = engine.evaluate(
        "database",
        identity_allowed=True,
        data_allowed=True,
        threat_safe=True,
    )
    assert result.allowed is True
    assert result.executable is False


def test_m52_8_fail_safe():
    state = SecurityFailSafe().evaluate(
        security_valid=False,
        evidence_preserved=False,
    )
    assert state is SecurityFailSafeState.EVIDENCE_PRESERVATION


def test_m52_9_denial_precedence():
    result = UnifiedSecurityPolicyPlane().evaluate(
        request_valid=True,
        identity_allowed=True,
        host_safe=False,
        threat_safe=True,
        data_allowed=True,
        governance_allowed=True,
    )
    assert result.decision is SecurityEnforcementDecision.DENY


def test_m52_10_runtime():
    runtime = UnifiedSecurityRuntime()

    result = runtime.evaluate(
        actor_id="employee-1",
        request_id="request-1",
        source_id="desktop-1",
    )

    assert result.requires_human_approval is True
    assert result.executable is False
    assert result.execution_authorized is False

    status = runtime.status()

    assert status["m52_active"] is True
    assert status["unified_policy_plane"] is True
    assert status["cross_layer_enforcement"] is True
    assert status["final_enforcement_boundary"] is True
    assert status["execution_authority"] is False
    assert status["self_authorized_execution"] is False
