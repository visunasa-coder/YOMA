from yoma.office.identity import (
    IdentityRegistryAdapter,
    SystemIdentity,
    UserIdentity,
)


class TestRegistry(IdentityRegistryAdapter):
    name = "test_registry"

    def health(self):
        return {"status": "healthy"}

    def get_user(self, user_id):
        users = {
            "U001": UserIdentity(
                user_id="U001",
                name="Test User",
                username="test.user",
                department="Engineering",
                role="Engineer",
                system_id="S001",
            )
        }
        return users.get(user_id)

    def list_users(self):
        user = self.get_user("U001")
        return [user] if user else []

    def get_system(self, system_id):
        systems = {
            "S001": SystemIdentity(
                system_id="S001",
                name="Engineering PC",
                system_number="SYS-001",
            )
        }
        return systems.get(system_id)

    def list_systems(self):
        system = self.get_system("S001")
        return [system] if system else []

    def resolve_user(self, external_id):
        return self.get_user(external_id)


def test_identity_models():
    user = UserIdentity(
        user_id="U001",
        name="Vishal",
        username="vishal",
    )

    system = SystemIdentity(
        system_id="S001",
        name="Office PC",
        system_number="SYS-001",
    )

    assert user.user_id == "U001"
    assert user.username == "vishal"
    assert system.system_number == "SYS-001"


def test_registry_contract():
    registry = TestRegistry()

    assert registry.health()["status"] == "healthy"
    assert registry.get_user("U001").name == "Test User"
    assert registry.get_system("S001").system_number == "SYS-001"
    assert len(registry.list_users()) == 1
    assert len(registry.list_systems()) == 1
    assert registry.resolve_user("U001").user_id == "U001"
