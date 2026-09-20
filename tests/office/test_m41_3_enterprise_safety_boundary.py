from yoma.office.enterprise_safety_boundary import EnterpriseSafetyBoundary


def validate(**overrides):
    values = {
        "human_approval_required": True,
        "execution_blocked": True,
        "authorization_explicit": True,
        "autonomous_execution_blocked": True,
    }
    values.update(overrides)
    return EnterpriseSafetyBoundary().validate(**values)


def test_complete_safety_boundary_is_safe():
    result = validate()
    assert result.safe is True


def test_human_approval_is_required():
    result = validate(human_approval_required=False)
    assert result.safe is False


def test_execution_must_remain_blocked():
    result = validate(execution_blocked=False)
    assert result.safe is False
    assert result.execution_blocked is False


def test_authorization_must_be_explicit():
    result = validate(authorization_explicit=False)
    assert result.safe is False


def test_autonomous_execution_must_be_blocked():
    result = validate(autonomous_execution_blocked=False)
    assert result.safe is False


def test_multiple_boundary_failures_are_visible():
    result = validate(
        human_approval_required=False,
        execution_blocked=False,
    )
    assert result.safe is False
    assert result.human_approval_required is False
    assert result.execution_blocked is False


def test_issues_are_deduplicated():
    result = validate(
        issues=("approval", "approval", "execution"),
    )
    assert result.issues == ("approval", "execution")


def test_result_always_requires_human_approval():
    result = validate()
    assert result.requires_human_approval is True


def test_result_is_not_executable():
    result = validate()
    assert result.executable is False


def test_serialization_preserves_boundary():
    result = validate()
    data = result.as_dict()
    assert data["safe"] is True
    assert data["human_approval_required"] is True
    assert data["execution_blocked"] is True
    assert data["executable"] is False


def test_partial_boundary_invalidates_result():
    result = validate(
        authorization_explicit=False,
        autonomous_execution_blocked=False,
    )
    assert result.safe is False


def test_boundary_is_deterministic():
    first = validate(issues=("approval", "execution"))
    second = validate(issues=("approval", "execution"))
    assert first == second


def test_ready_layers_cannot_override_execution_boundary():
    result = validate(
        human_approval_required=True,
        execution_blocked=True,
        authorization_explicit=True,
        autonomous_execution_blocked=False,
    )
    assert result.safe is False
    assert result.executable is False


def test_governance_flags_remain_intact_after_failure():
    result = validate(execution_blocked=False)
    assert result.requires_human_approval is True
    assert result.executable is False
