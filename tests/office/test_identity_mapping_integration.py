from pathlib import Path

from yoma.office.identity_mapping import (
    IdentityMapping,
    IdentityMappingPersistence,
)


def make_mapping(tmp_path: Path):
    persistence = IdentityMappingPersistence(
        tmp_path / "identity.db"
    )

    return IdentityMapping(
        persistence=persistence,
    )


def test_mapping_persists_new_identity(tmp_path):
    mapping = make_mapping(tmp_path)

    internal_id = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    persistence = IdentityMappingPersistence(
        tmp_path / "identity.db"
    )

    assert (
        persistence.get_internal_id(
            provider="company-registry",
            external_id="EMP001",
        )
        == internal_id
    )


def test_mapping_restores_existing_identity(tmp_path):
    db_path = tmp_path / "identity.db"

    first = IdentityMappingPersistence(db_path)

    first.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    second = IdentityMapping(
        persistence=IdentityMappingPersistence(db_path),
    )

    assert (
        second.map(
            provider="company-registry",
            external_id="EMP001",
        )
        == "yoma-001"
    )


def test_mapping_restart_keeps_same_identity(tmp_path):
    first = make_mapping(tmp_path)

    internal_id = first.map(
        provider="company-registry",
        external_id="EMP001",
    )

    second = make_mapping(tmp_path)

    assert (
        second.map(
            provider="company-registry",
            external_id="EMP001",
        )
        == internal_id
    )


def test_mapping_persists_multiple_identities(tmp_path):
    mapping = make_mapping(tmp_path)

    first = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    second = mapping.map(
        provider="company-registry",
        external_id="EMP002",
    )

    assert first != second
    assert mapping.count() == 2


def test_mapping_keeps_providers_isolated(tmp_path):
    mapping = make_mapping(tmp_path)

    hrms_id = mapping.map(
        provider="hrms",
        external_id="EMP001",
    )

    attendance_id = mapping.map(
        provider="attendance",
        external_id="EMP001",
    )

    assert hrms_id != attendance_id


def test_mapping_lookup_uses_persistence(tmp_path):
    db_path = tmp_path / "identity.db"

    persistence = IdentityMappingPersistence(db_path)

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    mapping = IdentityMapping(
        persistence=persistence,
    )

    assert (
        mapping.get_internal_id(
            provider="company-registry",
            external_id="EMP001",
        )
        == "yoma-001"
    )


def test_mapping_external_lookup_uses_persistence(tmp_path):
    db_path = tmp_path / "identity.db"

    persistence = IdentityMappingPersistence(db_path)

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    mapping = IdentityMapping(
        persistence=persistence,
    )

    assert mapping.get_external_identity("yoma-001") == {
        "provider": "company-registry",
        "external_id": "EMP001",
    }


def test_mapping_without_persistence_still_works():
    mapping = IdentityMapping()

    internal_id = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    assert mapping.count() == 1
    assert (
        mapping.get_internal_id(
            provider="company-registry",
            external_id="EMP001",
        )
        == internal_id
    )
