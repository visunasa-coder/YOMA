from pathlib import Path

import pytest

from yoma.db import initialize
from yoma.office.adapters.base import YomaAdapter
from yoma.office.integration import (
    Integration,
    IntegrationPersistence,
    IntegrationRuntimeManager,
)


class FakeAdapter(YomaAdapter):
    name = "test_integration"
    category = "test"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return ["test"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False


class FailingDisconnectAdapter(FakeAdapter):
    def disconnect(self):
        raise RuntimeError("disconnect failed")


class FailingConfigureAdapter(FakeAdapter):
    def configure(self, config):
        raise RuntimeError("configuration rejected")


def make_manager(tmp_path: Path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = IntegrationPersistence(db_path)

    manager = IntegrationRuntimeManager(
        persistence=persistence,
    )

    return manager, persistence


def test_duplicate_registration_is_rejected(tmp_path):
    manager, _ = make_manager(tmp_path)

    first = Integration(
        "test_integration",
        "company",
        "test",
    )

    second = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        first,
        FakeAdapter(),
    )

    with pytest.raises(ValueError):
        manager.register(
            second,
            FakeAdapter(),
        )


def test_unregister_removes_persistent_state(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        integration,
        FakeAdapter(),
    )

    assert persistence.load_all()

    assert manager.unregister(
        "test_integration"
    ) is True

    assert persistence.load_all() == []
    assert manager.status() == []


def test_unregister_unknown_integration_is_safe(tmp_path):
    manager, persistence = make_manager(tmp_path)

    assert manager.unregister(
        "does_not_exist"
    ) is False

    assert persistence.load_all() == []


def test_disable_connected_integration_persists_disabled_state(
    tmp_path,
):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    adapter = FakeAdapter()

    manager.register(
        integration,
        adapter,
    )

    manager.configure(
        "test_integration",
        {"value": "test"},
    )

    manager.connect("test_integration")

    assert manager.get(
        "test_integration"
    ).connected is True

    manager.disable("test_integration")

    restored_record = persistence.load_all()[0]

    assert restored_record["enabled"] is False
    assert manager.get(
        "test_integration"
    ).connected is False


def test_disconnect_failure_leaves_runtime_disconnected(
    tmp_path,
):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    adapter = FailingDisconnectAdapter()

    manager.register(
        integration,
        adapter,
    )

    manager.configure(
        "test_integration",
        {"value": "test"},
    )

    integration.set_connected(
        True,
        health={"status": "connected"},
    )

    with pytest.raises(RuntimeError):
        manager.disconnect("test_integration")

    assert manager.get(
        "test_integration"
    ).connected is False

    record = persistence.load_all()[0]

    assert record["status"] == "disconnected"


def test_failed_configuration_does_not_persist_new_configuration(
    tmp_path,
):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        integration,
        FailingConfigureAdapter(),
    )

    with pytest.raises(RuntimeError):
        manager.configure(
            "test_integration",
            {"secret": "should_not_persist"},
        )

    record = persistence.load_all()[0]

    assert record["configured"] is False
    assert record["configuration"] == {}


def test_re_register_after_unregister_is_allowed(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        integration,
        FakeAdapter(),
    )

    assert manager.unregister(
        "test_integration"
    ) is True

    replacement = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        replacement,
        FakeAdapter(),
    )

    assert len(manager.status()) == 1
    assert len(persistence.load_all()) == 1


def test_status_does_not_expose_configuration(tmp_path):
    manager, _ = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        integration,
        FakeAdapter(),
    )

    manager.configure(
        "test_integration",
        {
            "api_key": "super-secret",
            "password": "hidden",
        },
    )

    status = manager.status()[0]

    assert "configuration" not in status
    assert "api_key" not in str(status)
    assert "super-secret" not in str(status)
    assert "password" not in str(status)


def test_enable_after_disable_restores_enabled_state(tmp_path):
    manager, persistence = make_manager(tmp_path)

    integration = Integration(
        "test_integration",
        "company",
        "test",
    )

    manager.register(
        integration,
        FakeAdapter(),
    )

    manager.disable("test_integration")
    manager.enable("test_integration")

    record = persistence.load_all()[0]

    assert record["enabled"] is True
    assert manager.get(
        "test_integration"
    ).enabled is True
