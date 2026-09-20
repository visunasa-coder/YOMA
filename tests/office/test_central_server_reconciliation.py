import pytest

from yoma.office.central_server import CentralServerAdapter


def make_adapter():
    return CentralServerAdapter(
        name="company-central-server",
    )


def test_first_user_reconciliation_is_initial_snapshot():
    adapter = make_adapter()

    result = adapter.reconcile_users(
        [
            {"id": "EMP001", "name": "Vishal"},
            {"id": "EMP002", "name": "Employee Two"},
        ]
    )

    assert result["initial"] is True
    assert result["added"] == ["EMP001", "EMP002"]
    assert result["removed"] == []
    assert result["updated"] == []
    assert result["unchanged"] == []


def test_user_reconciliation_detects_added_user():
    adapter = make_adapter()

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )

    result = adapter.reconcile_users(
        [
            {"id": "EMP001", "name": "Vishal"},
            {"id": "EMP002", "name": "Employee Two"},
        ]
    )

    assert result["initial"] is False
    assert result["added"] == ["EMP002"]
    assert result["removed"] == []
    assert result["updated"] == []
    assert result["unchanged"] == ["EMP001"]


def test_user_reconciliation_detects_removed_user():
    adapter = make_adapter()

    adapter.reconcile_users(
        [
            {"id": "EMP001", "name": "Vishal"},
            {"id": "EMP002", "name": "Employee Two"},
        ]
    )

    result = adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )

    assert result["added"] == []
    assert result["removed"] == ["EMP002"]
    assert result["updated"] == []
    assert result["unchanged"] == ["EMP001"]


def test_user_reconciliation_detects_updated_user():
    adapter = make_adapter()

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal", "department": "Research"}]
    )

    result = adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal", "department": "Operations"}]
    )

    assert result["added"] == []
    assert result["removed"] == []
    assert result["updated"] == ["EMP001"]
    assert result["unchanged"] == []


def test_user_reconciliation_detects_reactivation():
    adapter = make_adapter()

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal", "active": False}]
    )

    result = adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal", "active": True}]
    )

    assert result["updated"] == ["EMP001"]


def test_user_reconciliation_detects_newly_inactive_user():
    adapter = make_adapter()

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal", "active": True}]
    )

    result = adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal", "active": False}]
    )

    assert result["updated"] == ["EMP001"]


def test_first_system_reconciliation_is_initial_snapshot():
    adapter = make_adapter()

    result = adapter.reconcile_systems(
        [
            {"id": "SYS001", "name": "Central Server"},
            {"id": "SYS002", "name": "Backup Server"},
        ]
    )

    assert result["initial"] is True
    assert result["added"] == ["SYS001", "SYS002"]
    assert result["removed"] == []
    assert result["updated"] == []
    assert result["unchanged"] == []


def test_system_reconciliation_detects_added_and_removed():
    adapter = make_adapter()

    adapter.reconcile_systems(
        [
            {"id": "SYS001", "name": "Central Server"},
            {"id": "SYS002", "name": "Backup Server"},
        ]
    )

    result = adapter.reconcile_systems(
        [
            {"id": "SYS001", "name": "Central Server"},
            {"id": "SYS003", "name": "New Server"},
        ]
    )

    assert result["added"] == ["SYS003"]
    assert result["removed"] == ["SYS002"]
    assert result["updated"] == []
    assert result["unchanged"] == ["SYS001"]


def test_system_reconciliation_detects_update():
    adapter = make_adapter()

    adapter.reconcile_systems(
        [{"id": "SYS001", "name": "Central Server"}]
    )

    result = adapter.reconcile_systems(
        [{"id": "SYS001", "name": "Production Server"}]
    )

    assert result["updated"] == ["SYS001"]
    assert result["unchanged"] == []


def test_reconciliation_is_deterministic():
    adapter = make_adapter()

    records = [
        {"id": "EMP003", "name": "Employee Three"},
        {"id": "EMP001", "name": "Employee One"},
        {"id": "EMP002", "name": "Employee Two"},
    ]

    first = adapter.reconcile_users(records)

    second = adapter.reconcile_users(records)

    assert first["initial"] is True
    assert second["initial"] is False
    assert second["added"] == []
    assert second["removed"] == []
    assert second["updated"] == []
    assert second["unchanged"] == ["EMP001", "EMP002", "EMP003"]


def test_invalid_user_reconciliation_does_not_replace_snapshot():
    adapter = make_adapter()

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )

    with pytest.raises(ValueError):
        adapter.reconcile_users(
            [
                {"id": "EMP001", "name": "Vishal"},
                {"name": "Missing ID"},
            ]
        )

    result = adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )

    assert result["added"] == []
    assert result["removed"] == []
    assert result["updated"] == []
    assert result["unchanged"] == ["EMP001"]
