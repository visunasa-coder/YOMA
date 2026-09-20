import pytest

from yoma.office.identity import (
    IdentityRegistryAdapter,
    IdentityRegistryManager,
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
            (user for user in self.list_users() if user.user_id == user_id),
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
            ),
            SystemIdentity(
                system_id="SYS002",
                name="Attendance Server",
                system_number="002",
            ),
        ]

    def get_system(self, system_id):
        return next(
            (
                system
                for system in self.list_systems()
                if system.system_id == system_id
            ),
            None,
        )


def make_manager():
    return IdentityRegistryManager(MockIdentityProvider())


def test_manager_exposes_provider():
    manager = make_manager()

    assert manager.provider == "company-registry"


def test_manager_health():
    manager = make_manager()

    health = manager.health()

    assert health["status"] == "healthy"
    assert health["provider"] == "company-registry"


def test_manager_status():
    manager = make_manager()

    status = manager.status()

    assert status.adapter == "company-registry"
    assert status.healthy is True


def test_manager_get_user():
    manager = make_manager()

    user = manager.get_user("EMP001")

    assert user is not None
    assert user.name == "Vishal"


def test_manager_lists_users():
    manager = make_manager()

    users = manager.list_users()

    assert len(users) == 2
    assert users[0].user_id == "EMP001"


def test_manager_resolves_external_user():
    manager = make_manager()

    user = manager.resolve_user("EMP001")

    assert user is not None
    assert user.user_id == "EMP001"


def test_manager_get_system():
    manager = make_manager()

    system = manager.get_system("SYS001")

    assert system is not None
    assert system.name == "Central Server"


def test_manager_lists_systems():
    manager = make_manager()

    systems = manager.list_systems()

    assert len(systems) == 2
    assert systems[1].system_id == "SYS002"


def test_manager_rejects_empty_user_id():
    manager = make_manager()

    with pytest.raises(ValueError):
        manager.get_user("")


def test_manager_rejects_empty_external_id():
    manager = make_manager()

    with pytest.raises(ValueError):
        manager.resolve_user("")


def test_manager_rejects_empty_system_id():
    manager = make_manager()

    with pytest.raises(ValueError):
        manager.get_system("")
