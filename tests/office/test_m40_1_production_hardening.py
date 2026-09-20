from yoma.office.production_hardening import ProductionHardening


def assess(**overrides):
    values = {
        "configuration_valid": True,
        "secrets_protected": True,
        "execution_governed": True,
        "failures_isolated": True,
    }
    values.update(overrides)
    return ProductionHardening().assess(**values)


def test_all_hardening_checks_pass():
    result = assess()
    assert result.secure is True


def test_invalid_configuration_fails():
    result = assess(configuration_valid=False)
    assert result.secure is False


def test_unprotected_secrets_fail():
    result = assess(secrets_protected=False)
    assert result.secure is False


def test_ungoverned_execution_fails():
    result = assess(execution_governed=False)
    assert result.secure is False


def test_failure_isolation_required():
    result = assess(failures_isolated=False)
    assert result.secure is False


def test_multiple_failures_are_reported():
    result = assess(
        configuration_valid=False,
        secrets_protected=False,
    )
    assert result.secure is False
    assert result.configuration_valid is False
    assert result.secrets_protected is False


def test_issues_are_preserved():
    result = assess(issues=("configuration", "secrets"))
    assert result.issues == ("configuration", "secrets")


def test_result_is_governed():
    result = assess()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["secure"] is True
    assert data["configuration_valid"] is True


def test_empty_issues_are_tuple():
    result = assess()
    assert result.issues == ()


def test_hardening_is_deterministic():
    first = assess(issues=("a", "b"))
    second = assess(issues=("a", "b"))
    assert first == second
