from datetime import datetime, timezone

from yoma.office.actions import (
    ActionRequest,
    ControlledActionGateway,
)
from yoma.office.operations import OperationalAction


def make_action(
    action_type="workload.review",
    requires_approval=True,
):
    return OperationalAction(
        action_id="ACT001",
        action_type=action_type,
        target_user_id="U001",
        requires_approval=requires_approval,
    )


def make_request(
    action=None,
    approval_token=None,
):
    return ActionRequest(
        request_id="REQ001",
        action=action or make_action(),
        requested_by="admin",
        requested_at=datetime.now(timezone.utc),
        approval_token=approval_token,
    )


def test_gateway_registers_executor():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "workload.review",
        lambda action: {"reviewed": True},
    )

    assert gateway.list_actions() == ["workload.review"]


def test_duplicate_executor_rejected():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "workload.review",
        lambda action: {},
    )

    try:
        gateway.register_executor(
            "workload.review",
            lambda action: {},
        )
        assert False
    except ValueError:
        pass


def test_action_without_approval_is_denied():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "workload.review",
        lambda action: {"ok": True},
    )

    result = gateway.execute(
        make_request()
    )

    assert result.status == "denied"
    assert result.executed is False
    assert result.message == "approval_required"


def test_approved_action_executes():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "workload.review",
        lambda action: {
            "employee_id": action.target_user_id,
        },
    )

    result = gateway.execute(
        make_request(
            approval_token="APPROVED-001"
        )
    )

    assert result.status == "executed"
    assert result.executed is True
    assert result.data["employee_id"] == "U001"


def test_unsupported_action_is_denied():
    gateway = ControlledActionGateway()

    result = gateway.execute(
        make_request(
            action=make_action(
                action_type="unknown.action"
            ),
            approval_token="APPROVED",
        )
    )

    assert result.status == "denied"
    assert result.executed is False
    assert result.message == "action_not_supported"


def test_non_approval_action_can_execute():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: {"refreshed": True},
    )

    result = gateway.execute(
        make_request(
            action=make_action(
                action_type="system.refresh",
                requires_approval=False,
            )
        )
    )

    assert result.executed is True
    assert result.data["refreshed"] is True


def test_policy_can_deny_action():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "workload.review",
        lambda action: {},
    )

    gateway.add_policy(
        lambda request: (False, "policy_blocked")
    )

    result = gateway.execute(
        make_request(
            approval_token="APPROVED"
        )
    )

    assert result.status == "denied"
    assert result.message == "policy_blocked"
    assert result.executed is False


def test_policy_can_allow_action():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "workload.review",
        lambda action: {"ok": True},
    )

    gateway.add_policy(
        lambda request: (True, "allowed")
    )

    result = gateway.execute(
        make_request(
            approval_token="APPROVED"
        )
    )

    assert result.executed is True


def test_executor_result_can_be_empty():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: None,
    )

    result = gateway.execute(
        make_request(
            action=make_action(
                action_type="system.refresh",
                requires_approval=False,
            )
        )
    )

    assert result.executed is True
    assert result.data is None
