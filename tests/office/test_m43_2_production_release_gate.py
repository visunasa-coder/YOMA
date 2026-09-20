from yoma.office.production_release_gate import ProductionReleaseGate


def assess(**overrides):
    values = {
        "identity_valid": True,
        "commercial_candidate_valid": True,
        "enterprise_validation_valid": True,
        "deployment_valid": True,
        "hardening_valid": True,
        "licensing_valid": True,
    }
    values.update(overrides)
    return ProductionReleaseGate().assess(**values)


def test_all_release_gates_pass():
    result = assess()
    assert result.gate_passed is True
    assert result.approved is False


def test_identity_is_required():
    result = assess(identity_valid=False)
    assert result.gate_passed is False


def test_commercial_candidate_is_required():
    result = assess(commercial_candidate_valid=False)
    assert result.gate_passed is False


def test_enterprise_validation_is_required():
    result = assess(enterprise_validation_valid=False)
    assert result.gate_passed is False


def test_deployment_is_required():
    result = assess(deployment_valid=False)
    assert result.gate_passed is False


def test_hardening_is_required():
    result = assess(hardening_valid=False)
    assert result.gate_passed is False


def test_licensing_is_required():
    result = assess(licensing_valid=False)
    assert result.gate_passed is False


def test_multiple_gate_failures_are_visible():
    result = assess(
        deployment_valid=False,
        hardening_valid=False,
        licensing_valid=False,
    )
    assert result.gate_passed is False
    assert result.deployment_valid is False
    assert result.hardening_valid is False
    assert result.licensing_valid is False


def test_issues_are_deduplicated():
    result = assess(
        issues=("deployment", "deployment", "hardening"),
    )
    assert result.issues == ("deployment", "hardening")


def test_gate_does_not_self_approve_release():
    result = assess()
    assert result.gate_passed is True
    assert result.approved is False


def test_human_approval_remains_required():
    result = assess()
    assert result.requires_human_approval is True


def test_gate_is_not_executable():
    result = assess()
    assert result.executable is False


def test_failed_gate_remains_non_executable():
    result = assess(hardening_valid=False)
    assert result.gate_passed is False
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["gate_passed"] is True
    assert data["approved"] is False
    assert data["executable"] is False


def test_gate_is_deterministic():
    first = assess(issues=("deployment", "licensing"))
    second = assess(issues=("deployment", "licensing"))
    assert first == second


def test_gate_requires_every_release_layer():
    result = assess(
        identity_valid=True,
        commercial_candidate_valid=True,
        enterprise_validation_valid=True,
        deployment_valid=True,
        hardening_valid=True,
        licensing_valid=False,
    )
    assert result.gate_passed is False
