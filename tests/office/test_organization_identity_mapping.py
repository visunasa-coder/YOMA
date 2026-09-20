from pathlib import Path

from yoma.office.identity import (
    IdentityRegistryAdapter,
    IdentityRegistryManager,
    UserIdentity,
)
from yoma.office.identity_mapping import (
    IdentityMapping,
    IdentityMappingPersistence,
)
from yoma.office.organization import OrganizationIdentity


class MockIdentityProvider(IdentityRegistryAdapter):
    name = "company-registry"

    def health(self):
        return {"status": "healthy"}

    def list_users(self):
        return [
            UserIdentity(
                user_id="EMP001",
                name="Vishal",
                department="Research",
                role="Employee",
            ),
            UserIdentity(
                user_id="EMP002",
                name="Test User",
                department="Marketing",
                role="Manager",
            ),
        ]

    def get_user(self, user_id):
        return next(
            (u for u in self.list_users() if u.user_id == user_id),
            None,
        )

    def resolve_user(self, external_id):
        return self.get_user(external_id)

    def list_systems(self):
        return []

    def get_system(self, system_id):
        return None


def make_organization(tmp_path: Path):
    manager = IdentityRegistryManager(
        MockIdentityProvider()
    )

    organization = OrganizationIdentity(manager)

    mapping = IdentityMapping(
        persistence=IdentityMappingPersistence(
            tmp_path / "identity.db"
        )
    )

    return organization, mapping


def test_organization_user_can_be_mapped(tmp_path):
    organization, mapping = make_organization(tmp_path)

    user = organization.resolve_user("EMP001")

    assert user is not None

    internal_id = mapping.map(
        provider=organization.provider,
        external_id=user.user_id,
    )

    assert internal_id


def test_organization_user_mapping_is_stable(tmp_path):
    organization, mapping = make_organization(tmp_path)

    user = organization.resolve_user("EMP001")

    first = mapping.map(
        provider=organization.provider,
        external_id=user.user_id,
    )

    second = mapping.map(
        provider=organization.provider,
        external_id=user.user_id,
    )

    assert first == second


def test_multiple_organization_users_get_distinct_ids(tmp_path):
    organization, mapping = make_organization(tmp_path)

    user1 = organization.resolve_user("EMP001")
    user2 = organization.resolve_user("EMP002")

    first = mapping.map(
        provider=organization.provider,
        external_id=user1.user_id,
    )

    second = mapping.map(
        provider=organization.provider,
        external_id=user2.user_id,
    )

    assert first != second


def test_organization_mapping_survives_restart(tmp_path):
    organization, first_mapping = make_organization(tmp_path)

    user = organization.resolve_user("EMP001")

    internal_id = first_mapping.map(
        provider=organization.provider,
        external_id=user.user_id,
    )

    _, second_mapping = make_organization(tmp_path)

    assert (
        second_mapping.map(
            provider=organization.provider,
            external_id=user.user_id,
        )
        == internal_id
    )


def test_organization_mapping_can_reverse_resolve(tmp_path):
    organization, mapping = make_organization(tmp_path)

    user = organization.resolve_user("EMP001")

    internal_id = mapping.map(
        provider=organization.provider,
        external_id=user.user_id,
    )

    assert mapping.get_external_identity(internal_id) == {
        "provider": "company-registry",
        "external_id": "EMP001",
    }


def test_unknown_organization_user_is_not_mapped(tmp_path):
    organization, mapping = make_organization(tmp_path)

    user = organization.resolve_user("UNKNOWN")

    assert user is None
    assert mapping.count() == 0
