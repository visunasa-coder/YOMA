from yoma.office.production_release_identity import ProductionReleaseIdentity
from yoma.office.production_release_runtime import ProductionReleaseRuntime


def assess(**overrides):
    values = {
        "identity": ProductionReleaseIdentity(),
        "commercial_candidate_valid": True,
        "enterprise_validation_valid": True,
        "deployment_valid": True,
        "hardening_valid": True,
        "licensing_valid": True,
    }
    values.update(overrides)
    return ProductionReleaseRuntime().assess(**values)


def test_complete_production_release_is_ready():
    result = assess()
    assert result.ready is True
    assert result.production_release is True


def test_identity_failure_blocks_release():
    result = assess(
        identity=ProductionReleaseIdentity(version="2.0.0"),
    )
    assert result.ready is False
    assert result.identity_valid is False


def test_commercial_candidate_failure_blocks_release():
    result = assess(commercial_candidate_valid=False)
    assert result.ready is False
    assert result.commercial_candidate_valid is False


def test_enterprise_validation_failure_blocks_release():
    result = assess(enterprise_validation_valid=False)
    assert result.ready is False


def test_deployment_failure_blocks_release():
    result = assess(deployment_valid=False)
    assert result.ready is False


def test_hardening_failure_blocks_release():
    result = assess(hardening_valid=False)
    assert result.ready is False


def test_licensing_failure_blocks_release():
    result = assess(licensing_valid=False)
    assert result.ready is False


def test_release_gate_must_pass():
    result = assess(hardening_valid=False)
    assert result.release_gate_passed is False


def test_safety_must_pass():
    result = assess(execution_blocked=False)
    assert result.ready is False
    assert result.safety_valid is False


def test_human_approval_is_required():
    result = assess(human_approval_required=False)
    assert result.ready is False


def test_explicit_authorization_is_required():
    result = assess(explicit_authorization_required=False)
    assert result.ready is False


def test_autonomous_release_must_remain_blocked():
    result = assess(autonomous_release_blocked=False)
    assert result.ready is False


def test_release_authorization_defaults_to_false():
    result = assess()
    assert result.release_authorized is False


def test_authorization_does_not_create_execution_authority():
    result = assess(release_authorized=True)
    assert result.ready is True
    assert result.release_authorized is True
    assert result.executable is False
    assert result.requires_human_approval is True


def test_result_is_always_governed():
    result = assess()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_failed_release_remains_non_executable():
    result = assess(commercial_candidate_valid=False)
    assert result.ready is False
    assert result.production_release is False
    assert result.executable is False


def test_issues_are_preserved():
    result = assess(issues=("deployment", "licensing"))
    assert result.issues == ("deployment", "licensing")


def test_issues_are_deduplicated():
    result = assess(issues=("deployment", "deployment", "licensing"))
    assert result.issues == ("deployment", "licensing")


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["ready"] is True
    assert data["production_release"] is True
    assert data["release_gate_passed"] is True
    assert data["safety_valid"] is True
    assert data["executable"] is False


def test_runtime_is_deterministic():
    first = assess(issues=("deployment", "licensing"))
    second = assess(issues=("deployment", "licensing"))
    assert first == second


def test_release_requires_every_gate():
    result = assess(
        enterprise_validation_valid=False,
        deployment_valid=False,
        hardening_valid=False,
        licensing_valid=False,
    )
    assert result.ready is False
    assert result.release_gate_passed is False


def test_authorized_release_still_requires_safe_handoff():
    result = assess(
        release_authorized=True,
        execution_blocked=True,
        autonomous_release_blocked=True,
    )
    assert result.ready is True
    assert result.release_authorized is True
    assert result.executable is False
