import pytest

from yoma.office.central_server import CentralServerAdapter
from yoma.office.identity_mapping import IdentityMapping, IdentityMappingPersistence


def make_adapter():
    return CentralServerAdapter(
        name="company-central-server",
    )


def test_sync_users_persists_normalized_identities(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    result = adapter.sync_users(
        [
            {
                "id": "EMP001",
                "name": "Vishal",
                "department": "Research",
            }
        ]
    )

    internal_id = mapping.map(
        provider=adapter.name,
        external_id=result[0].user_id,
    )

    assert internal_id
    assert mapping.count() == 1


def test_sync_systems_persists_normalized_identities(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    result = adapter.sync_systems(
        [
            {
                "id": "SYS001",
                "name": "Central Server",
                "system_number": "001",
            }
        ]
    )

    internal_id = mapping.map(
        provider=adapter.name,
        external_id=result[0].system_id,
    )

    assert internal_id
    assert mapping.count() == 1


def test_repeated_user_sync_does_not_duplicate_mapping(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    first = adapter.sync_users(
        [{"id": "EMP001", "name": "Vishal"}]
    )
    second = adapter.sync_users(
        [{"id": "EMP001", "name": "Vishal Updated"}]
    )

    first_id = mapping.map(
        provider=adapter.name,
        external_id=first[0].user_id,
    )
    second_id = mapping.map(
        provider=adapter.name,
        external_id=second[0].user_id,
    )

    assert first_id == second_id
    assert mapping.count() == 1


def test_repeated_system_sync_does_not_duplicate_mapping(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    first = adapter.sync_systems(
        [{"id": "SYS001", "name": "Central Server"}]
    )
    second = adapter.sync_systems(
        [{"id": "SYS001", "name": "Central Server Updated"}]
    )

    first_id = mapping.map(
        provider=adapter.name,
        external_id=first[0].system_id,
    )
    second_id = mapping.map(
        provider=adapter.name,
        external_id=second[0].system_id,
    )

    assert first_id == second_id
    assert mapping.count() == 1


def test_user_mapping_survives_new_mapping_instance(tmp_path):
    db_path = tmp_path / "identity.db"
    persistence = IdentityMappingPersistence(db_path)
    mapping = IdentityMapping(persistence=persistence)

    internal_id = mapping.map(
        provider="company-central-server",
        external_id="EMP001",
    )

    restored_persistence = IdentityMappingPersistence(db_path)
    restored = IdentityMapping(persistence=restored_persistence)

    assert restored.get_internal_id(
        provider="company-central-server",
        external_id="EMP001",
    ) == internal_id


def test_system_mapping_survives_new_mapping_instance(tmp_path):
    db_path = tmp_path / "identity.db"
    persistence = IdentityMappingPersistence(db_path)
    mapping = IdentityMapping(persistence=persistence)

    internal_id = mapping.map(
        provider="company-central-server",
        external_id="SYS001",
    )

    restored_persistence = IdentityMappingPersistence(db_path)
    restored = IdentityMapping(persistence=restored_persistence)

    assert restored.get_internal_id(
        provider="company-central-server",
        external_id="SYS001",
    ) == internal_id


def test_user_and_system_mappings_are_distinct(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)

    user_id = mapping.map(
        provider="company-central-server",
        external_id="001",
    )
    system_id = mapping.map(
        provider="company-central-server",
        external_id="001",
    )

    assert user_id == system_id


def test_inactive_user_mapping_is_persisted(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    result = adapter.sync_users(
        [
            {
                "id": "EMP001",
                "name": "Former Employee",
                "active": False,
            }
        ]
    )

    internal_id = mapping.map(
        provider=adapter.name,
        external_id=result[0].user_id,
    )

    assert internal_id
    assert result[0].active is False


def test_inactive_system_mapping_is_persisted(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    result = adapter.sync_systems(
        [
            {
                "id": "SYS001",
                "name": "Retired Server",
                "active": False,
            }
        ]
    )

    internal_id = mapping.map(
        provider=adapter.name,
        external_id=result[0].system_id,
    )

    assert internal_id
    assert result[0].active is False


def test_invalid_user_sync_does_not_create_mapping(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    with pytest.raises(ValueError):
        adapter.sync_users([{"name": "Missing ID"}])

    assert mapping.count() == 0


def test_invalid_system_sync_does_not_create_mapping(tmp_path):
    persistence = IdentityMappingPersistence(tmp_path / "identity.db")
    mapping = IdentityMapping(persistence=persistence)
    adapter = make_adapter()

    with pytest.raises(ValueError):
        adapter.sync_systems([{"name": "Missing ID"}])

    assert mapping.count() == 0
