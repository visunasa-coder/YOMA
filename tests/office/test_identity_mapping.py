import pytest

from yoma.office.identity_mapping import IdentityMapping


def make_mapping():
    return IdentityMapping()


def test_mapping_starts_empty():
    mapping = make_mapping()

    assert mapping.count() == 0


def test_mapping_creates_internal_identity():
    mapping = make_mapping()

    internal_id = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    assert internal_id
    assert mapping.count() == 1


def test_mapping_returns_same_internal_identity():
    mapping = make_mapping()

    first = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    second = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    assert first == second
    assert mapping.count() == 1


def test_different_external_ids_get_different_internal_ids():
    mapping = make_mapping()

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


def test_different_providers_can_use_same_external_id():
    mapping = make_mapping()

    first = mapping.map(
        provider="hrms",
        external_id="EMP001",
    )

    second = mapping.map(
        provider="attendance",
        external_id="EMP001",
    )

    assert first != second
    assert mapping.count() == 2


def test_lookup_internal_identity():
    mapping = make_mapping()

    internal_id = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    assert (
        mapping.get_internal_id(
            provider="company-registry",
            external_id="EMP001",
        )
        == internal_id
    )


def test_lookup_external_identity():
    mapping = make_mapping()

    internal_id = mapping.map(
        provider="company-registry",
        external_id="EMP001",
    )

    result = mapping.get_external_identity(internal_id)

    assert result == {
        "provider": "company-registry",
        "external_id": "EMP001",
    }


def test_unknown_mapping_returns_none():
    mapping = make_mapping()

    assert (
        mapping.get_internal_id(
            provider="company-registry",
            external_id="UNKNOWN",
        )
        is None
    )


def test_mapping_rejects_empty_provider():
    mapping = make_mapping()

    with pytest.raises(ValueError):
        mapping.map(
            provider="",
            external_id="EMP001",
        )


def test_mapping_rejects_empty_external_id():
    mapping = make_mapping()

    with pytest.raises(ValueError):
        mapping.map(
            provider="company-registry",
            external_id="",
        )
