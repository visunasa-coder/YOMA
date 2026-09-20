import pytest

from yoma.office.central_server import CentralServerAdapter
from yoma.office.organization_state import OrganizationStatePersistence


def make_adapter(db_path=None):
    if db_path is None:
        return CentralServerAdapter(
            name="company-central-server",
        )

    persistence = OrganizationStatePersistence(db_path)

    return CentralServerAdapter(
        name="company-central-server",
        organization_state_persistence=persistence,
    )


def test_user_snapshot_is_persisted(tmp_path):
    adapter = make_adapter(tmp_path / "organization.db")

    result = adapter.reconcile_users(
        [
            {
                "id": "EMP001",
                "name": "Vishal",
                "department": "Research",
            }
        ]
    )

    assert result["initial"] is True

    snapshot = adapter.organization_state.users()

    assert len(snapshot) == 1
    assert snapshot[0].user_id == "EMP001"
    assert snapshot[0].name == "Vishal"


def test_system_snapshot_is_persisted(tmp_path):
    adapter = make_adapter(tmp_path / "organization.db")

    result = adapter.reconcile_systems(
        [
            {
                "id": "SYS001",
                "name": "Central Server",
                "system_number": "001",
            }
        ]
    )

    assert result["initial"] is True

    snapshot = adapter.organization_state.systems()

    assert len(snapshot) == 1
    assert snapshot[0].system_id == "SYS001"
    assert snapshot[0].name == "Central Server"


def test_user_snapshot_survives_new_adapter(tmp_path):
    db_path = tmp_path / "organization.db"

    first = make_adapter(db_path)

    first.reconcile_users(
        [
            {
                "id": "EMP001",
                "name": "Vishal",
                "department": "Research",
            }
        ]
    )

    second = make_adapter(db_path)

    snapshot = second.organization_state.users()

    assert len(snapshot) == 1
    assert snapshot[0].user_id == "EMP001"
    assert snapshot[0].name == "Vishal"
    assert snapshot[0].department == "Research"


def test_system_snapshot_survives_new_adapter(tmp_path):
    db_path = tmp_path / "organization.db"

    first = make_adapter(db_path)

    first.reconcile_systems(
        [
            {
                "id": "SYS001",
                "name": "Central Server",
            }
        ]
    )

    second = make_adapter(db_path)

    snapshot = second.organization_state.systems()

    assert len(snapshot) == 1
    assert snapshot[0].system_id == "SYS001"
    assert snapshot[0].name == "Central Server"


def test_updated_user_replaces_persisted_snapshot(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [
            {
                "id": "EMP001",
                "name": "Vishal",
                "department": "Research",
            }
        ]
    )

    adapter.reconcile_users(
        [
            {
                "id": "EMP001",
                "name": "Vishal Updated",
                "department": "Operations",
            }
        ]
    )

    restored = make_adapter(db_path)

    snapshot = restored.organization_state.users()

    assert len(snapshot) == 1
    assert snapshot[0].name == "Vishal Updated"
    assert snapshot[0].department == "Operations"


def test_removed_user_is_removed_from_persisted_snapshot(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [
            {"id": "EMP001", "name": "Vishal"},
            {"id": "EMP002", "name": "Employee Two"},
        ]
    )

    adapter.reconcile_users(
        [
            {"id": "EMP001", "name": "Vishal"},
        ]
    )

    restored = make_adapter(db_path)

    snapshot = restored.organization_state.users()

    assert [user.user_id for user in snapshot] == ["EMP001"]


def test_removed_system_is_removed_from_persisted_snapshot(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_systems(
        [
            {"id": "SYS001", "name": "Central Server"},
            {"id": "SYS002", "name": "Backup Server"},
        ]
    )

    adapter.reconcile_systems(
        [
            {"id": "SYS001", "name": "Central Server"},
        ]
    )

    restored = make_adapter(db_path)

    snapshot = restored.organization_state.systems()

    assert [system.system_id for system in snapshot] == ["SYS001"]


def test_inactive_user_state_is_persisted(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [
            {
                "id": "EMP001",
                "name": "Former Employee",
                "active": False,
            }
        ]
    )

    restored = make_adapter(db_path)

    snapshot = restored.organization_state.users()

    assert snapshot[0].active is False


def test_inactive_system_state_is_persisted(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_systems(
        [
            {
                "id": "SYS001",
                "name": "Retired Server",
                "active": False,
            }
        ]
    )

    restored = make_adapter(db_path)

    snapshot = restored.organization_state.systems()

    assert snapshot[0].active is False


def test_empty_user_snapshot_is_persisted(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users([])

    restored = make_adapter(db_path)

    assert restored.organization_state.users() == []


def test_empty_system_snapshot_is_persisted(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_systems([])

    restored = make_adapter(db_path)

    assert restored.organization_state.systems() == []


def test_invalid_user_reconciliation_does_not_modify_persisted_snapshot(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )

    with pytest.raises(ValueError):
        adapter.reconcile_users(
            [
                {"id": "EMP001", "name": "Corrupted"},
                {"name": "Missing ID"},
            ]
        )

    restored = make_adapter(db_path)

    snapshot = restored.organization_state.users()

    assert len(snapshot) == 1
    assert snapshot[0].user_id == "EMP001"
    assert snapshot[0].name == "Vishal"


def test_user_and_system_snapshots_are_independent(tmp_path):
    db_path = tmp_path / "organization.db"

    adapter = make_adapter(db_path)

    adapter.reconcile_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )

    adapter.reconcile_systems(
        [{"id": "SYS001", "name": "Central Server"}]
    )

    restored = make_adapter(db_path)

    assert [user.user_id for user in restored.organization_state.users()] == [
        "EMP001"
    ]

    assert [
        system.system_id
        for system in restored.organization_state.systems()
    ] == ["SYS001"]
