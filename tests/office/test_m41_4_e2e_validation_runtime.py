from yoma.office.e2e_validation_runtime import E2EValidationRuntime


DEFAULT_STAGES = (
    "event",
    "intelligence",
    "control",
    "background",
    "licensing",
    "deployment",
    "hardening",
)


def validate(**overrides):
    values = {
        "stages": DEFAULT_STAGES,
        "events_valid": True,
        "intelligence_valid": True,
        "control_valid": True,
        "background_valid": True,
        "licensing_valid": True,
        "deployment_valid": True,
        "hardening_valid": True,
        "execution_governed": True,
        "human_approval_required": True,
        "execution_blocked": True,
        "authorization_explicit": True,
        "autonomous_execution_blocked": True,
    }
    values.update(overrides)
    return E2EValidationRuntime().validate(**values)


def test_complete_e2e_validation_is_valid():
    result = validate()
    assert result.valid is True
    assert result.enterprise_valid is True
    assert result.workflow_valid is True
    assert result.safety_valid is True


def test_enterprise_failure_invalidates_runtime():
    result = validate(deployment_valid=False)
    assert result.valid is False
    assert result.enterprise_valid is False


def test_workflow_failure_invalidates_runtime():
    result = validate(
        stages=("event", "intelligence", "control"),
    )
    assert result.valid is False
    assert result.workflow_valid is False


def test_safety_failure_invalidates_runtime():
    result = validate(execution_blocked=False)
    assert result.valid is False
    assert result.safety_valid is False


def test_execution_governance_failure_invalidates_runtime():
    result = validate(execution_governed=False)
    assert result.valid is False


def test_human_approval_boundary_is_required():
    result = validate(human_approval_required=False)
    assert result.valid is False


def test_explicit_authorization_is_required():
    result = validate(authorization_explicit=False)
    assert result.valid is False


def test_autonomous_execution_must_remain_blocked():
    result = validate(autonomous_execution_blocked=False)
    assert result.valid is False


def test_all_layers_must_pass():
    result = validate(
        events_valid=False,
        licensing_valid=False,
        hardening_valid=False,
    )
    assert result.valid is False


def test_issues_are_preserved():
    result = validate(issues=("deployment", "safety"))
    assert result.issues == ("deployment", "safety")


def test_issues_are_deduplicated():
    result = validate(
        issues=("deployment", "deployment", "safety"),
    )
    assert result.issues == ("deployment", "safety")


def test_result_is_governed():
    result = validate()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = validate()
    data = result.as_dict()
    assert data["valid"] is True
    assert data["enterprise_valid"] is True
    assert data["workflow_valid"] is True
    assert data["safety_valid"] is True
    assert data["executable"] is False


def test_failed_validation_remains_non_executable():
    result = validate(deployment_valid=False)
    assert result.valid is False
    assert result.executable is False
    assert result.requires_human_approval is True


def test_runtime_is_deterministic():
    first = validate(issues=("deployment", "safety"))
    second = validate(issues=("deployment", "safety"))
    assert first == second
