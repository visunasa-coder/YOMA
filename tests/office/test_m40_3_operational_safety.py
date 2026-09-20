from yoma.office.operational_safety import OperationalSafety


def assess(**overrides):
    values = {
        "audit_enabled": True,
        "traceable": True,
        "approval_boundary_intact": True,
        "execution_blocked": True,
    }
    values.update(overrides)
    return OperationalSafety().assess(**values)


def test_all_safety_checks_pass():
    result = assess()
    assert result.safe is True


def test_audit_is_required():
    result = assess(audit_enabled=False)
    assert result.safe is False
    assert result.audit_enabled is False


def test_traceability_is_required():
    result = assess(traceable=False)
    assert result.safe is False


def test_approval_boundary_is_required():
    result = assess(approval_boundary_intact=False)
    assert result.safe is False


def test_execution_must_remain_blocked():
    result = assess(execution_blocked=False)
    assert result.safe is False
    assert result.execution_blocked is False


def test_multiple_safety_failures_are_preserved():
    result = assess(
        audit_enabled=False,
        approval_boundary_intact=False,
    )
    assert result.safe is False
    assert result.audit_enabled is False
    assert result.approval_boundary_intact is False


def test_issues_are_deduplicated():
    result = assess(
        issues=("audit", "audit", "approval"),
    )
    assert result.issues == ("audit", "approval")


def test_result_is_governed():
    result = assess()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = assess()
    data = result.as_dict()
    assert data["safe"] is True
    assert data["execution_blocked"] is True


def test_safety_assessment_is_deterministic():
    first = assess(issues=("audit", "traceability"))
    second = assess(issues=("audit", "traceability"))
    assert first == second


def test_issue_values_are_string_normalized():
    result = assess(issues=(1, 2))
    assert result.issues == ("1", "2")


def test_execution_boundary_cannot_be_marked_safe_when_open():
    result = assess(execution_blocked=False)
    assert result.safe is False
    assert result.executable is False
    assert result.requires_human_approval is True
