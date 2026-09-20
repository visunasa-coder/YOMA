from yoma.office.commercial_readiness import CommercialReadiness


def assess(**overrides):
    values = {
        "product_identity_valid": True,
        "release_manifest_valid": True,
        "integrity_available": True,
        "licensing_ready": True,
        "deployment_ready": True,
        "hardening_ready": True,
        "enterprise_validation_ready": True,
    }
    values.update(overrides)
    return CommercialReadiness().assess(**values)


def test_complete_release_is_ready():
    result = assess()
    assert result.ready is True


def test_product_identity_is_required():
    result = assess(product_identity_valid=False)
    assert result.ready is False


def test_release_manifest_is_required():
    result = assess(release_manifest_valid=False)
    assert result.ready is False


def test_integrity_is_required():
    result = assess(integrity_available=False)
    assert result.ready is False


def test_licensing_is_required():
    result = assess(licensing_ready=False)
    assert result.ready is False


def test_deployment_is_required():
    result = assess(deployment_ready=False)
    assert result.ready is False


def test_hardening_is_required():
    result = assess(hardening_ready=False)
    assert result.ready is False


def test_enterprise_validation_is_required():
    result = assess(enterprise_validation_ready=False)
    assert result.ready is False


def test_multiple_failures_are_visible():
    result = assess(
        licensing_ready=False,
        deployment_ready=False,
        hardening_ready=False,
    )
    assert result.ready is False
    assert result.licensing_ready is False
    assert result.deployment_ready is False
    assert result.hardening_ready is False


def test_issues_are_deduplicated():
    result = assess(
        issues=("licensing", "licensing", "deployment"),
    )
    assert result.issues == ("licensing", "deployment")


def test_result_is_governed():
    result = assess()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["ready"] is True
    assert data["integrity_available"] is True


def test_readiness_is_deterministic():
    first = assess(issues=("licensing", "deployment"))
    second = assess(issues=("licensing", "deployment"))
    assert first == second


def test_failed_readiness_remains_non_executable():
    result = assess(release_manifest_valid=False)
    assert result.ready is False
    assert result.executable is False
    assert result.requires_human_approval is True
