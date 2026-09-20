from pathlib import Path

from yoma.db import initialize
from yoma.office.adapters import YomaAdapter
from yoma.office.integration import Integration, IntegrationRuntimeManager
from yoma.office.integration.persistence import IntegrationPersistence


class FakeAdapter(YomaAdapter):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.category = "integration"

    def capabilities(self) -> list[str]:
        return [
            "connect",
            "disconnect",
            "health",
            "collect",
        ]

    def connect(self, config: dict) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> dict:
        return {"status": "healthy"}

    def collect_events(self):
        return ()


def make_manager(tmp_path: Path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = IntegrationPersistence(db_path)
    manager = IntegrationRuntimeManager(
        persistence=persistence,
    )

    return manager, persistence


def test_runtime_persists_registration(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    manager.register(
        integration,
        FakeAdapter("central_server"),
    )

    records = persistence.load_all()

    assert len(records) == 1
    assert records[0]["name"] == "central_server"


def test_runtime_persists_configuration(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    manager.register(
        integration,
        FakeAdapter("central_server"),
    )

    manager.configure(
        "central_server",
        {"endpoint": "https://central.example"},
    )

    record = persistence.load_all()[0]

    assert record["configured"] is True
    assert record["configuration"]["endpoint"] == (
        "https://central.example"
    )


def test_restore_recreates_integration(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    manager.register(
        integration,
        FakeAdapter("central_server"),
    )

    manager.configure(
        "central_server",
        {"system_number": "SYS001"},
    )

    restarted = IntegrationRuntimeManager(
        persistence=persistence,
    )

    restored = restarted.restore()

    assert len(restored) == 1
    assert restored[0].name == "central_server"
    assert restored[0].provider == "company"
    assert restored[0].configured is True
    assert restored[0].configuration()["system_number"] == "SYS001"


def test_restore_never_restores_active_connection(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    manager.register(
        integration,
        FakeAdapter("central_server"),
    )

    manager.configure(
        "central_server",
        {"endpoint": "https://central.example"},
    )

    integration.set_connected(
        True,
        health={"status": "connected"},
    )

    persistence.save(integration)

    restarted = IntegrationRuntimeManager(
        persistence=persistence,
    )

    restored = restarted.restore()

    assert restored[0].connected is False


def test_disabled_state_restores(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "attendance",
        "company",
        "attendance",
    )

    manager.register(
        integration,
        FakeAdapter("attendance"),
    )

    manager.disable("attendance")

    restarted = IntegrationRuntimeManager(
        persistence=persistence,
    )

    restored = restarted.restore()

    assert restored[0].enabled is False


def test_restore_is_idempotent(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "google_workspace",
        "google",
        "workspace",
    )

    manager.register(
        integration,
        FakeAdapter("google_workspace"),
    )

    restarted = IntegrationRuntimeManager(
        persistence=persistence,
    )

    first = restarted.restore()
    second = restarted.restore()

    assert len(first) == 1
    assert len(second) == 0
    assert len(restarted.status()) == 1
