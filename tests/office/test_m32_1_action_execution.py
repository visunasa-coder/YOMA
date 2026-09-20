from datetime import datetime, timezone

import pytest

from yoma.office.action_execution import (
    ActionExecutionGateway,
    ExecutionResult,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def successful_executor(**kwargs):
    return {
        "action_id": kwargs["action_id"],
        "action_type": kwargs["action_type"],
        "executed": True,
    }


def failing_executor(**kwargs):
    raise RuntimeError("controlled executor failure")


def test_gateway_starts_empty():
    gateway = ActionExecutionGateway()

    assert gateway.records == ()
    assert gateway.executor_names == ()


def test_executor_registration():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        successful_executor,
    )

    assert gateway.executor_names == ("test_executor",)


def test_executor_duplicate_registration_rejected():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        successful_executor,
    )

    with pytest.raises(ValueError):
        gateway.register_executor(
            "test_executor",
            successful_executor,
        )


def test_unapproved_action_is_rejected():
    gateway = ActionExecutionGateway()

    result = gateway.execute(
        action_id="ACT-M32-1",
        action_type="workload.review",
        executor_name="test_executor",
        approved=False,
        created_at=NOW,
    )

    assert isinstance(result, ExecutionResult)
    assert result.status == "rejected"
    assert result.executable is False
    assert result.requires_human_approval is True


def test_unregistered_executor_is_blocked():
    gateway = ActionExecutionGateway()

    with pytest.raises(ValueError):
        gateway.execute_approved(
            action_id="ACT-M32-2",
            action_type="workload.review",
            executor_name="missing",
            created_at=NOW,
        )


def test_successful_execution():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        successful_executor,
    )

    result = gateway.execute_approved(
        action_id="ACT-M32-3",
        action_type="workload.review",
        executor_name="test_executor",
        created_at=NOW,
        parameters={"employee_id": "U1"},
    )

    assert result.execution_id == "EXEC-ACT-M32-3"
    assert result.status == "succeeded"
    assert result.output["executed"] is True
    assert result.executable is True


def test_execution_record_is_persisted_in_memory():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        successful_executor,
    )

    result = gateway.execute_approved(
        action_id="ACT-M32-4",
        action_type="workload.review",
        executor_name="test_executor",
        created_at=NOW,
    )

    record = gateway.get_record(result.execution_id)

    assert record is not None
    assert record.execution_id == result.execution_id
    assert record.status == "succeeded"
    assert record.action_id == "ACT-M32-4"


def test_executor_failure_is_captured():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "failing_executor",
        failing_executor,
    )

    result = gateway.execute_approved(
        action_id="ACT-M32-5",
        action_type="workload.review",
        executor_name="failing_executor",
        created_at=NOW,
    )

    assert result.status == "failed"
    assert "controlled executor failure" in result.error


def test_duplicate_execution_is_blocked():
    gateway = ActionExecutionGateway()

    gateway.register_executor(
        "test_executor",
        successful_executor,
    )

    gateway.execute_approved(
        action_id="ACT-M32-6",
        action_type="workload.review",
        executor_name="test_executor",
        created_at=NOW,
    )

    with pytest.raises(ValueError):
        gateway.execute_approved(
            action_id="ACT-M32-6",
            action_type="workload.review",
            executor_name="test_executor",
            created_at=NOW,
        )


def test_execution_is_deterministic():
    first = ActionExecutionGateway()
    second = ActionExecutionGateway()

    first.register_executor(
        "test_executor",
        successful_executor,
    )
    second.register_executor(
        "test_executor",
        successful_executor,
    )

    result_a = first.execute_approved(
        action_id="ACT-M32-7",
        action_type="workload.review",
        executor_name="test_executor",
        created_at=NOW,
        parameters={"employee_id": "U1"},
    )

    result_b = second.execute_approved(
        action_id="ACT-M32-7",
        action_type="workload.review",
        executor_name="test_executor",
        created_at=NOW,
        parameters={"employee_id": "U1"},
    )

    assert result_a == result_b
