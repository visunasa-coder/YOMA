from yoma.office.production_hardening_runtime import ProductionHardeningRuntime


def assess(**overrides):
    values = {
        "configuration_valid": True,
        "secrets_protected": True,
        "execution_governed": True,
        "failures_isolated": True,
        "components": ("runtime", "event_bus", "intelligence"),
        "failed_components": (),
        "audit_enabled": True,
        "traceable": True,
        "approval_boundary_intact": True,
        "execution_blocked": True,
    }
    values.update(overrides)
    return ProductionHardeningRuntime().assess(**values)


def test_runtime_is_ready_when_all_checks_pass():
    result = assess()
    assert result.ready is True
    assert result.secure is True
    assert result.failure_isolated is True
    assert result.operationally_safe is True


def test_configuration_failure_blocks_readiness():
    result = assess(configuration_valid=False)
    assert result.ready is False
    assert result.secure is False


def test_secret_failure_blocks_readiness():
    result = assess(secrets_protected=False)
    assert result.ready is False


def test_governance_failure_blocks_readiness():
    result = assess(execution_governed=False)
    assert result.ready is False


def test_runtime_isolation_failure_blocks_readiness():
    result = assess(failures_isolated=False)
    assert result.ready is False


def test_audit_failure_blocks_readiness():
    result = assess(audit_enabled=False)
    assert result.ready is False
    assert result.operationally_safe is False


def test_traceability_failure_blocks_readiness():
    result = assess(traceable=False)
    assert result.ready is False


def test_approval_boundary_failure_blocks_readiness():
    result = assess(approval_boundary_intact=False)
    assert result.ready is False


def test_execution_boundary_must_remain_blocked():
    result = assess(execution_blocked=False)
    assert result.ready is False
    assert result.executable is False


def test_failed_components_are_not_execution_authority():
    result = assess(failed_components=("event_bus",))
    assert result.ready is True
    assert result.executable is False


def test_issues_are_preserved():
    result = assess(issues=("configuration", "audit"))
    assert result.issues == ("configuration", "audit")


def test_result_is_governed():
    result = assess()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["ready"] is True
    assert data["secure"] is True
    assert data["failure_isolated"] is True
    assert data["operationally_safe"] is True


def test_runtime_is_deterministic():
    first = assess(issues=("configuration", "audit"))
    second = assess(issues=("configuration", "audit"))
    assert first == second


def test_multiple_failures_remain_visible():
    result = assess(
        configuration_valid=False,
        audit_enabled=False,
        traceable=False,
    )
    assert result.ready is False
    assert result.secure is False
    assert result.operationally_safe is False
