from yoma.office.production_release_safety import ProductionReleaseSafety


def assess(**overrides):
    values = {
        "human_approval_required": True,
        "explicit_authorization_required": True,
        "execution_blocked": True,
        "autonomous_release_blocked": True,
    }
    values.update(overrides)
    return ProductionReleaseSafety().assess(**values)


def test_complete_release_boundary_is_safe():
    result = assess()
    assert result.safe is True


def test_human_approval_is_required():
    result = assess(human_approval_required=False)
    assert result.safe is False


def test_explicit_authorization_is_required():
    result = assess(explicit_authorization_required=False)
    assert result.safe is False


def test_execution_must_remain_blocked():
    result = assess(execution_blocked=False)
    assert result.safe is False


def test_autonomous_release_must_be_blocked():
    result = assess(autonomous_release_blocked=False)
    assert result.safe is False


def test_release_authorization_defaults_to_false():
    result = assess()
    assert result.release_authorized is False


def test_authorization_does_not_make_result_executable():
    result = assess(release_authorized=True)
    assert result.safe is True
    assert result.executable is False
    assert result.requires_human_approval is True


def test_multiple_boundary_failures_are_visible():
    result = assess(
        human_approval_required=False,
        execution_blocked=False,
    )
    assert result.safe is False
    assert result.human_approval_required is False
    assert result.execution_blocked is False


def test_issues_are_deduplicated():
    result = assess(
        issues=("approval", "approval", "execution"),
    )
    assert result.issues == ("approval", "execution")


def test_result_requires_human_approval():
    result = assess()
    assert result.requires_human_approval is True


def test_result_is_not_executable():
    result = assess()
    assert result.executable is False


def test_failed_boundary_remains_non_executable():
    result = assess(execution_blocked=False)
    assert result.safe is False
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["safe"] is True
    assert data["execution_blocked"] is True
    assert data["release_authorized"] is False
    assert data["executable"] is False


def test_boundary_is_deterministic():
    first = assess(issues=("approval", "execution"))
    second = assess(issues=("approval", "execution"))
    assert first == second


def test_authorized_release_still_requires_execution_handoff():
    result = assess(
        release_authorized=True,
        execution_blocked=True,
    )
    assert result.release_authorized is True
    assert result.execution_blocked is True
    assert result.executable is False


def test_all_safety_controls_are_required():
    result = assess(
        human_approval_required=True,
        explicit_authorization_required=True,
        execution_blocked=True,
        autonomous_release_blocked=False,
    )
    assert result.safe is False
