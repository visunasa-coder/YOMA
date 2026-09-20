from datetime import datetime, timezone

from yoma.office.actions import (
    ActionRequest,
    ControlledActionGateway,
)
from yoma.office.governance import (
    AuditLog,
    GovernedActionExecutor,
    PolicyDecision,
    PolicyEngine,
)
from yoma.office.operations import OperationalAction


def make_request(
    action_type="system.refresh",
    approval_token=None,
):
    action = OperationalAction(
        action_id="ACT001",
        action_type=action_type,
        target_system_id="SYS001",
        requires_approval=approval_token is not None,
    )

    return ActionRequest(
        request_id="REQ001",
        action=action,
        requested_by="admin",
        requested_at=datetime.now(timezone.utc),
        approval_token=approval_token,
    )


def test_policy_engine_defaults_to_allow():
    engine = PolicyEngine()

    decision = engine.evaluate(
        make_request()
    )

    assert decision.allowed is True


def test_policy_can_block():
    engine = PolicyEngine()

    engine.register(
        "block_all",
        lambda request: PolicyDecision(
            allowed=False,
            reason="blocked_for_test",
        ),
    )

    decision = engine.evaluate(
        make_request()
    )

    assert decision.allowed is False
    assert decision.reason == "blocked_for_test"


def test_policy_list():
    engine = PolicyEngine()

    engine.register(
        "test_policy",
        lambda request: PolicyDecision(True, "ok"),
    )

    assert engine.list_policies() == ["test_policy"]


def test_duplicate_policy_rejected():
    engine = PolicyEngine()

    engine.register(
        "test_policy",
        lambda request: PolicyDecision(True, "ok"),
    )

    try:
        engine.register(
            "test_policy",
            lambda request: PolicyDecision(True, "ok"),
        )
        assert False
    except ValueError:
        pass


def test_audit_log_records_event():
    audit = AuditLog()

    record = audit.record(
        audit_id="AUD001",
        event_type="action.requested",
        actor="admin",
        request_id="REQ001",
        action_type="system.refresh",
        status="requested",
    )

    assert record.audit_id == "AUD001"
    assert audit.count() == 1
    assert audit.list()[0] == record


def test_audit_removes_secrets():
    audit = AuditLog()

    record = audit.record(
        audit_id="AUD001",
        event_type="action.requested",
        actor="admin",
        request_id="REQ001",
        action_type="system.refresh",
        status="requested",
        metadata={
            "token": "SECRET",
            "password": "SECRET2",
            "normal": "safe",
        },
    )

    assert "token" not in record.metadata
    assert "password" not in record.metadata
    assert record.metadata["normal"] == "safe"


def test_governed_execution():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: {"refreshed": action.target_system_id},
    )

    governed = GovernedActionExecutor(gateway)

    result = governed.execute(
        make_request()
    )

    assert result.executed is True
    assert governed.audit_log.count() == 2


def test_governed_policy_block():
    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: {"refreshed": True},
    )

    policies = PolicyEngine()

    policies.register(
        "security_block",
        lambda request: PolicyDecision(
            False,
            "security_policy_block",
        ),
    )

    audit = AuditLog()

    governed = GovernedActionExecutor(
        gateway,
        policies,
        audit,
    )

    result = governed.execute(
        make_request()
    )

    assert result.executed is False
    assert result.message == "security_policy_block"
    assert audit.count() == 1


def test_policy_invalid_result_rejected():
    engine = PolicyEngine()

    engine.register(
        "bad",
        lambda request: "invalid",
    )

    try:
        engine.evaluate(make_request())
        assert False
    except TypeError:
        pass
