from yoma.office.identity import (
    IdentityRegistryManager,
    IdentityRegistryAdapter,
    SystemIdentity,
    UserIdentity,
)


class TestRegistry(IdentityRegistryAdapter):
    name = "test_registry"

    def health(self):
        return {"status": "healthy"}

    def get_user(self, user_id):
        if user_id == "U001":
            return UserIdentity(
                user_id="U001",
                name="Test User",
                username="test.user",
                department="Engineering",
                role="Engineer",
                system_id="S001",
            )
        return None

    def list_users(self):
        return [
            UserIdentity(
                user_id="U001",
                name="Test User",
            )
        ]

    def get_system(self, system_id):
        if system_id == "S001":
            return SystemIdentity(
                system_id="S001",
                name="Engineering PC",
                system_number="SYS-001",
            )
        return None

    def list_systems(self):
        return [
            SystemIdentity(
                system_id="S001",
                name="Engineering PC",
                system_number="SYS-001",
            )
        ]

    def resolve_user(self, external_id):
        return self.get_user(external_id)


def test_manager_provider_and_health():
    manager = IdentityRegistryManager(TestRegistry())

    assert manager.provider == "test_registry"
    assert manager.health()["status"] == "healthy"

    status = manager.status()

    assert status.adapter == "test_registry"
    assert status.healthy is True


def test_manager_resolves_users():
    manager = IdentityRegistryManager(TestRegistry())

    user = manager.get_user(" U001 ")

    assert user is not None
    assert user.name == "Test User"

    users = manager.list_users()

    assert len(users) == 1


def test_manager_resolves_systems():
    manager = IdentityRegistryManager(TestRegistry())

    system = manager.get_system(" S001 ")

    assert system is not None
    assert system.system_number == "SYS-001"

    systems = manager.list_systems()

    assert len(systems) == 1


def test_manager_resolves_external_identity():
    manager = IdentityRegistryManager(TestRegistry())

    user = manager.resolve_user("U001")

    assert user is not None
    assert user.user_id == "U001"


def test_manager_rejects_empty_identifiers():
    manager = IdentityRegistryManager(TestRegistry())

    for operation in (
        lambda: manager.get_user(""),
        lambda: manager.get_system(""),
        lambda: manager.resolve_user(""),
    ):
        try:
            operation()
            assert False, "Expected ValueError"
        except ValueError:
            pass
