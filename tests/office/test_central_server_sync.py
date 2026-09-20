import pytest

from yoma.office.central_server import CentralServerAdapter


def make_adapter():
    return CentralServerAdapter(
        name="company-central-server",
    )


def test_sync_users_normalizes_records():
    adapter = make_adapter()

    result = adapter.sync_users(
        [
            {
                "id": "EMP001",
                "name": "Vishal",
                "department": "Research",
            },
            {
                "id": "EMP002",
                "name": "Employee Two",
                "department": "Operations",
            },
        ]
    )

    assert len(result) == 2
    assert result[0].user_id == "EMP001"
    assert result[0].name == "Vishal"
    assert result[1].user_id == "EMP002"


def test_sync_systems_normalizes_records():
    adapter = make_adapter()

    result = adapter.sync_systems(
        [
            {
                "id": "SYS001",
                "name": "Central Server",
                "system_number": "001",
            },
            {
                "id": "SYS002",
                "name": "Backup Server",
                "system_number": "002",
            },
        ]
    )

    assert len(result) == 2
    assert result[0].system_id == "SYS001"
    assert result[1].system_id == "SYS002"


def test_sync_users_preserves_inactive_state():
    adapter = make_adapter()

    result = adapter.sync_users(
        [
            {
                "id": "EMP001",
                "name": "Active Employee",
                "active": True,
            },
            {
                "id": "EMP002",
                "name": "Former Employee",
                "active": False,
            },
        ]
    )

    assert result[0].active is True
    assert result[1].active is False


def test_sync_systems_preserves_inactive_state():
    adapter = make_adapter()

    result = adapter.sync_systems(
        [
            {
                "id": "SYS001",
                "active": True,
            },
            {
                "id": "SYS002",
                "active": False,
            },
        ]
    )

    assert result[0].active is True
    assert result[1].active is False


def test_sync_users_rejects_invalid_collection():
    adapter = make_adapter()

    with pytest.raises(TypeError):
        adapter.sync_users("invalid")


def test_sync_systems_rejects_invalid_collection():
    adapter = make_adapter()

    with pytest.raises(TypeError):
        adapter.sync_systems("invalid")


def test_sync_users_rejects_malformed_record():
    adapter = make_adapter()

    with pytest.raises(ValueError):
        adapter.sync_users(
            [
                {
                    "name": "Missing ID",
                }
            ]
        )


def test_sync_systems_rejects_malformed_record():
    adapter = make_adapter()

    with pytest.raises(ValueError):
        adapter.sync_systems(
            [
                {
                    "name": "Missing ID",
                }
            ]
        )


def test_sync_users_empty_collection():
    adapter = make_adapter()

    result = adapter.sync_users([])

    assert result == []


def test_sync_systems_empty_collection():
    adapter = make_adapter()

    result = adapter.sync_systems([])

    assert result == []
