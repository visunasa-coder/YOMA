from yoma.office.cross_layer_workflow_validation import (
    CrossLayerWorkflowValidation,
)


def validate(**overrides):
    values = {
        "stages": (
            "event",
            "intelligence",
            "control",
            "background",
            "licensing",
            "deployment",
            "hardening",
        ),
    }
    values.update(overrides)
    return CrossLayerWorkflowValidation().validate(**values)


def test_complete_workflow_is_valid():
    result = validate()
    assert result.valid is True
    assert result.workflow_order_valid is True


def test_event_stage_is_required():
    result = validate(event_stage=False)
    assert result.valid is False


def test_intelligence_stage_is_required():
    result = validate(intelligence_stage=False)
    assert result.valid is False


def test_control_stage_is_required():
    result = validate(control_stage=False)
    assert result.valid is False


def test_background_stage_is_required():
    result = validate(background_stage=False)
    assert result.valid is False


def test_licensing_stage_is_required():
    result = validate(licensing_stage=False)
    assert result.valid is False


def test_deployment_stage_is_required():
    result = validate(deployment_stage=False)
    assert result.valid is False


def test_hardening_stage_is_required():
    result = validate(hardening_stage=False)
    assert result.valid is False


def test_workflow_order_is_required():
    result = validate(
        stages=(
            "event",
            "control",
            "intelligence",
            "background",
            "licensing",
            "deployment",
            "hardening",
        )
    )
    assert result.valid is False
    assert result.workflow_order_valid is False


def test_missing_stage_invalidates_workflow():
    result = validate(
        stages=(
            "event",
            "intelligence",
            "control",
            "background",
            "licensing",
            "deployment",
        )
    )
    assert result.valid is False


def test_duplicate_stages_are_normalized():
    result = validate(
        stages=(
            "event",
            "event",
            "intelligence",
            "control",
            "background",
            "licensing",
            "deployment",
            "hardening",
        )
    )
    assert result.valid is True


def test_stage_names_are_case_normalized():
    result = validate(
        stages=(
            "EVENT",
            "INTELLIGENCE",
            "CONTROL",
            "BACKGROUND",
            "LICENSING",
            "DEPLOYMENT",
            "HARDENING",
        )
    )
    assert result.valid is True


def test_issues_are_deduplicated():
    result = validate(
        issues=("licensing", "licensing", "deployment"),
    )
    assert result.issues == ("licensing", "deployment")


def test_result_is_governed():
    result = validate()
    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = validate()
    data = result.as_dict()
    assert data["valid"] is True
    assert data["workflow_order_valid"] is True


def test_validation_is_deterministic():
    first = validate(issues=("event", "deployment"))
    second = validate(issues=("event", "deployment"))
    assert first == second
