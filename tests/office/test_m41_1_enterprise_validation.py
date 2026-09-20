from yoma.office.enterprise_validation import EnterpriseValidation


def validate(**overrides):
    values = {
        "events_valid": True,
        "intelligence_valid": True,
        "control_valid": True,
        "background_valid": True,
        "licensing_valid": True,
        "deployment_valid": True,
        "hardening_valid": True,
        "execution_governed": True,
    }
    values.update(overrides)
    return EnterpriseValidation().validate(**values)


def test_complete_enterprise_stack_is_valid():
    result = validate()
    assert result.valid is True


def test_event_layer_is_required():
    result = validate(events_valid=False)
    assert result.valid is False
    assert result.events_valid is False


def test_intelligence_layer_is_required():
    result = validate(intelligence_valid=False)
    assert result.valid is False


def test_control_layer_is_required():
    result = validate(control_valid=False)
    assert result.valid is False


def test_background_layer_is_required():
    result = validate(background_valid=False)
    assert result.valid is False


def test_licensing_layer_is_required():
    result = validate(licensing_valid=False)
    assert result.valid is False


def test_deployment_layer_is_required():
    result = validate(deployment_valid=False)
    assert result.valid is False


def test_hardening_layer_is_required():
    result = validate(hardening_valid=False)
    assert result.valid is False


def test_execution_governance_is_required():
    result = validate(execution_governed=False)
    assert result.valid is False
    assert result.execution_governed is False


def test_multiple_layer_failures_are_visible():
    result = validate(
        events_valid=False,
        licensing_valid=False,
        deployment_valid=False,
    )
    assert result.valid is False
    assert result.events_valid is False
    assert result.licensing_valid is False
    assert result.deployment_valid is False


def test_issues_are_deduplicated():
    result = validate(
        issues=("deployment", "deployment", "licensing"),
    )
    assert result.issues == ("deployment", "licensing")


def test_result_is_governed():
    result = validate()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = validate()
    data = result.as_dict()
    assert data["valid"] is True
    assert data["hardening_valid"] is True
    assert data["execution_governed"] is True


def test_validation_is_deterministic():
    first = validate(issues=("events", "deployment"))
    second = validate(issues=("events", "deployment"))
    assert first == second
