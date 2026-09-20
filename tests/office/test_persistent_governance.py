import json
import sqlite3

from yoma.office.governance.persistent import PersistentAuditLog


def make_connection():
    connection = sqlite3.connect(":memory:")

    connection.execute(
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

    return connection


def test_persistent_audit_writes_existing_schema():
    connection = make_connection()

    audit = PersistentAuditLog(connection)

    audit.record(
        event_type="action.executed",
        actor="admin",
        request_id="REQ001",
        action_type="system.refresh",
        status="executed",
    )

    row = connection.execute(
        """
        SELECT event_type, username, details_json
        FROM audit_events
        """
    ).fetchone()

    assert row[0] == "action.executed"
    assert row[1] == "admin"

    details = json.loads(row[2])

    assert details["request_id"] == "REQ001"
    assert details["action_type"] == "system.refresh"
    assert details["status"] == "executed"


def test_persistent_audit_preserves_reason():
    connection = make_connection()

    audit = PersistentAuditLog(connection)

    audit.record(
        event_type="action.denied",
        actor="admin",
        request_id="REQ002",
        action_type="system.refresh",
        status="denied",
        reason="security_policy_block",
    )

    row = connection.execute(
        "SELECT details_json FROM audit_events"
    ).fetchone()

    details = json.loads(row[0])

    assert details["reason"] == "security_policy_block"


def test_persistent_audit_removes_secrets():
    connection = make_connection()

    audit = PersistentAuditLog(connection)

    audit.record(
        event_type="action.requested",
        actor="admin",
        request_id="REQ003",
        action_type="system.refresh",
        status="requested",
        metadata={
            "token": "SUPER_SECRET",
            "password": "PASSWORD",
            "credential": "CREDENTIAL",
            "authorization": "BEARER SECRET",
            "safe_value": "allowed",
        },
    )

    row = connection.execute(
        "SELECT details_json FROM audit_events"
    ).fetchone()

    details = json.loads(row[0])

    assert "token" not in details
    assert "password" not in details
    assert "credential" not in details
    assert "authorization" not in details
    assert details["safe_value"] == "allowed"


def test_persistent_audit_supports_multiple_events():
    connection = make_connection()

    audit = PersistentAuditLog(connection)

    for index in range(3):
        audit.record(
            event_type="action.executed",
            actor="admin",
            request_id=f"REQ{index}",
            action_type="system.refresh",
            status="executed",
        )

    count = connection.execute(
        "SELECT COUNT(*) FROM audit_events"
    ).fetchone()[0]

    assert count == 3


def test_persistent_audit_allows_anonymous_actor():
    connection = make_connection()

    audit = PersistentAuditLog(connection)

    audit.record(
        event_type="system.event",
        actor=None,
        request_id="REQ004",
        action_type="system.refresh",
        status="executed",
    )

    row = connection.execute(
        "SELECT username FROM audit_events"
    ).fetchone()

    assert row[0] is None
