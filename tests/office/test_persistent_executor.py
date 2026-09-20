from datetime import datetime, timezone
import sqlite3

from yoma.office.actions import ActionRequest, ControlledActionGateway
from yoma.office.governance import (
    PersistentGovernedActionExecutor,
    PolicyDecision,
    PolicyEngine,
)
from yoma.office.operations import OperationalAction


def connection():
    db = sqlite3.connect(":memory:")

    db.execute(
        """
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            username TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    return db


def request(
    action_type="system.refresh",
    approval_token=None,
):
    return ActionRequest(
        request_id="REQ001",
        action=OperationalAction(
            action_id="ACT001",
            action_type=action_type,
            target_system_id="SYS001",
            requires_approval=approval_token is not None,
        ),
        requested_by="admin",
        requested_at=datetime.now(timezone.utc),
        approval_token=approval_token,
    )


def test_persistent_governed_execution():
    db = connection()

    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: {"system": action.target_system_id},
    )

    executor = PersistentGovernedActionExecutor(
        gateway,
        db,
    )

    result = executor.execute(request())

    assert result.executed is True

    rows = db.execute(
        "SELECT event_type FROM audit_events ORDER BY id"
    ).fetchall()

    assert [row[0] for row in rows] == [
        "action.authorized",
        "action.executed",
    ]


def test_persistent_governed_policy_denial():
    db = connection()

    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: {},
    )

    policies = PolicyEngine()

    policies.register(
        "deny",
        lambda req: PolicyDecision(
            False,
            "blocked",
        ),
    )

    executor = PersistentGovernedActionExecutor(
        gateway,
        db,
        policies,
    )

    result = executor.execute(request())

    assert result.executed is False
    assert result.message == "blocked"

    row = db.execute(
        "SELECT event_type FROM audit_events"
    ).fetchone()

    assert row[0] == "action.denied"


def test_persistent_governed_executor_does_not_store_token():
    db = connection()

    gateway = ControlledActionGateway()

    gateway.register_executor(
        "system.refresh",
        lambda action: {},
    )

    executor = PersistentGovernedActionExecutor(
        gateway,
        db,
    )

    executor.execute(
        request(approval_token="SUPER_SECRET_TOKEN")
    )

    details = db.execute(
        "SELECT details_json FROM audit_events"
    ).fetchall()

    combined = " ".join(row[0] for row in details)

    assert "SUPER_SECRET_TOKEN" not in combined


def test_executor_error_is_audited():
    db = connection()

    gateway = ControlledActionGateway()

    def failing_executor(action):
        raise RuntimeError("boom")

    gateway.register_executor(
        "system.refresh",
        failing_executor,
    )

    executor = PersistentGovernedActionExecutor(
        gateway,
        db,
    )

    try:
        executor.execute(request())
        assert False
    except RuntimeError:
        pass

    rows = db.execute(
        "SELECT event_type, details_json FROM audit_events ORDER BY id"
    ).fetchall()

    assert rows[0][0] == "action.authorized"
    assert rows[1][0] == "action.failed"
    assert "RuntimeError" in rows[1][1]
