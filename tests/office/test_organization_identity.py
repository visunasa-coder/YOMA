import pytest

from yoma.office.identity import (
    IdentityRegistryAdapter,
    IdentityRegistryManager,
    SystemIdentity,
    UserIdentity,
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
                username="vishal",
                email="vishal@example.com",
                department="Research",
                role="Employee",
                system_id="SYS001",
            ),
            UserIdentity(
                user_id="EMP002",
                name="Test User",
                username="testuser",
                department="Marketing",
                role="Manager",
                system_id="SYS001",
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
        return [
            SystemIdentity(
                system_id="SYS001",
                name="Central Server",
                system_number="001",
            )
        ]

    def get_system(self, system_id):
        return next(
            (s for s in self.list_systems() if s.system_id == system_id),
            None,
        )


def make_organization():
    manager = IdentityRegistryManager(MockIdentityProvider())

    return OrganizationIdentity(manager)


def test_organization_has_provider():
    organization = make_organization()

    assert organization.provider == "company-registry"


def test_organization_lists_users():
    organization = make_organization()

    users = organization.users()

    assert len(users) == 2
    assert users[0].user_id == "EMP001"


def test_organization_gets_user():
    organization = make_organization()

    user = organization.user("EMP001")

    assert user is not None
    assert user.name == "Vishal"


def test_organization_resolves_external_user():
    organization = make_organization()

    user = organization.resolve_user("EMP001")

    assert user is not None
    assert user.user_id == "EMP001"


def test_organization_lists_systems():
    organization = make_organization()

    systems = organization.systems()

    assert len(systems) == 1
    assert systems[0].system_id == "SYS001"


def test_organization_gets_system():
    organization = make_organization()

    system = organization.system("SYS001")

    assert system is not None
    assert system.name == "Central Server"


def test_organization_departments_are_normalized():
    organization = make_organization()

    departments = organization.departments()

    assert departments == ["Marketing", "Research"]


def test_organization_roles_are_normalized():
    organization = make_organization()

    roles = organization.roles()

    assert roles == ["Employee", "Manager"]


def test_organization_rejects_missing_manager():
    with pytest.raises(ValueError):
        OrganizationIdentity(None)
