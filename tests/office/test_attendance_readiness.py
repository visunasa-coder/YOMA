import pytest

from yoma.office.services.attendance_readiness import AttendanceReadiness


def assessment_with_candidate():
    return {
        "category": "attendance",
        "candidate_count": 1,
        "candidates": [
            {
                "adapter": "generic_attendance",
                "category": "attendance",
                "requires_human_approval": True,
                "executable": False,
            }
        ],
        "discovery_only": True,
        "requires_human_approval": True,
        "executable": False,
        "activation_allowed": False,
    }


def test_ready_when_installation_and_attendance_are_ready():
    result = AttendanceReadiness().assess(
        deployment_ready=True,
        assessment=assessment_with_candidate(),
    )

    assert result.ready is True
    assert result.installation_ready is True
    assert result.attendance_detected is True
    assert result.adapter_available is True
    assert result.configuration_required is True


def test_not_ready_when_deployment_is_not_ready():
    result = AttendanceReadiness().assess(
        deployment_ready=False,
        assessment=assessment_with_candidate(),
    )

    assert result.ready is False
    assert result.installation_ready is False
    assert result.attendance_detected is True


def test_not_ready_when_no_attendance_is_detected():
    result = AttendanceReadiness().assess(
        deployment_ready=True,
        assessment={
            "category": "attendance",
            "candidate_count": 0,
            "candidates": [],
        },
    )

    assert result.ready is False
    assert result.attendance_detected is False
    assert result.adapter_available is False
    assert result.configuration_required is False


def test_unrecognized_adapter_is_not_available():
    result = AttendanceReadiness().assess(
        deployment_ready=True,
        assessment={
            "candidate_count": 1,
            "candidates": [
                {
                    "adapter": "unknown_adapter",
                    "category": "attendance",
                }
            ],
        },
    )

    assert result.ready is False
    assert result.attendance_detected is True
    assert result.adapter_available is False
    assert result.configuration_required is True


def test_result_requires_human_approval():
    result = AttendanceReadiness().assess(
        deployment_ready=True,
        assessment=assessment_with_candidate(),
    )

    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = AttendanceReadiness().assess(
        deployment_ready=True,
        assessment=assessment_with_candidate(),
    )

    data = result.as_dict()

    assert data["ready"] is True
    assert data["candidate_count"] == 1
    assert data["adapter_available"] is True
    assert data["requires_human_approval"] is True
    assert data["executable"] is False


def test_invalid_assessment_type():
    with pytest.raises(TypeError):
        AttendanceReadiness().assess(
            deployment_ready=True,
            assessment=None,
        )


def test_invalid_deployment_ready_type():
    with pytest.raises(TypeError):
        AttendanceReadiness().assess(
            deployment_ready="yes",
            assessment=assessment_with_candidate(),
        )


def test_negative_candidate_count_rejected():
    with pytest.raises(ValueError):
        AttendanceReadiness().assess(
            deployment_ready=True,
            assessment={
                "candidate_count": -1,
                "candidates": [],
            },
        )


def test_candidate_count_type_rejected():
    with pytest.raises(TypeError):
        AttendanceReadiness().assess(
            deployment_ready=True,
            assessment={
                "candidate_count": "1",
                "candidates": [],
            },
        )


def test_no_execution_authority():
    result = AttendanceReadiness().assess(
        deployment_ready=True,
        assessment=assessment_with_candidate(),
    )

    assert result.requires_human_approval is True
    assert result.executable is False
