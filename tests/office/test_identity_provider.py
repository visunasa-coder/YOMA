import pytest

from yoma.office.identity import (
    IdentityRegistryAdapter,
    SystemIdentity,
    UserIdentity,
)


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
            )
        ]

    def get_user(self, user_id):
        for user in self.list_users():
            if user.user_id == user_id:
                return user
        return None

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
        for system in self.list_systems():
            if system.system_id == system_id:
                return system
        return None


def make_provider():
    return MockIdentityProvider()


def test_provider_has_identity():
    provider = make_provider()

    assert provider.name == "company-registry"
    assert provider.category == "identity_registry"


def test_provider_lists_users():
    provider = make_provider()

    users = provider.list_users()

    assert len(users) == 1
    assert users[0].user_id == "EMP001"


def test_provider_gets_user_by_id():
    provider = make_provider()

    user = provider.get_user("EMP001")

    assert user is not None
    assert user.name == "Vishal"


def test_provider_returns_none_for_unknown_user():
    provider = make_provider()

    assert provider.get_user("UNKNOWN") is None


def test_provider_resolves_external_user_id():
    provider = make_provider()

    user = provider.resolve_user("EMP001")

    assert user is not None
    assert user.user_id == "EMP001"


def test_provider_lists_systems():
    provider = make_provider()

    systems = provider.list_systems()

    assert len(systems) == 1
    assert systems[0].system_id == "SYS001"


def test_provider_gets_system_by_id():
    provider = make_provider()

    system = provider.get_system("SYS001")

    assert system is not None
    assert system.name == "Central Server"


def test_provider_health():
    provider = make_provider()

    health = provider.health()

    assert health["status"] == "healthy"
