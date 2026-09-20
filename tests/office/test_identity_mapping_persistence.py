from pathlib import Path

from yoma.office.identity_mapping import IdentityMappingPersistence


def make_persistence(tmp_path: Path):
    return IdentityMappingPersistence(
        tmp_path / "identity.db"
    )


def test_persistence_starts_empty(tmp_path):
    persistence = make_persistence(tmp_path)

    assert persistence.count() == 0


def test_persistence_saves_mapping(tmp_path):
    persistence = make_persistence(tmp_path)

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    assert persistence.count() == 1


def test_persistence_loads_mapping(tmp_path):
    persistence = make_persistence(tmp_path)

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    result = persistence.get_internal_id(
        provider="company-registry",
        external_id="EMP001",
    )

    assert result == "yoma-001"


def test_persistence_survives_new_instance(tmp_path):
    db_path = tmp_path / "identity.db"

    first = IdentityMappingPersistence(db_path)

    first.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    second = IdentityMappingPersistence(db_path)

    assert (
        second.get_internal_id(
            provider="company-registry",
            external_id="EMP001",
        )
        == "yoma-001"
    )


def test_persistence_loads_external_identity(tmp_path):
    persistence = make_persistence(tmp_path)

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    result = persistence.get_external_identity("yoma-001")

    assert result == {
        "provider": "company-registry",
        "external_id": "EMP001",
    }


def test_persistence_does_not_duplicate_mapping(tmp_path):
    persistence = make_persistence(tmp_path)

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    persistence.save(
        provider="company-registry",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    assert persistence.count() == 1


def test_persistence_supports_multiple_providers(tmp_path):
    persistence = make_persistence(tmp_path)

    persistence.save(
        provider="hrms",
        external_id="EMP001",
        internal_id="yoma-001",
    )

    persistence.save(
        provider="attendance",
        external_id="EMP001",
        internal_id="yoma-002",
    )

    assert persistence.count() == 2


def test_unknown_mapping_returns_none(tmp_path):
    persistence = make_persistence(tmp_path)

    assert (
        persistence.get_internal_id(
            provider="company-registry",
            external_id="UNKNOWN",
        )
        is None
    )
