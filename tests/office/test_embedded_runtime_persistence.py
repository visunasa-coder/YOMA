from pathlib import Path

from yoma.db import initialize
from yoma.office.adapters.base import YomaAdapter
from yoma.office.integration import (
    Integration,
    IntegrationPersistence,
    IntegrationRuntimeManager,
)
from yoma.office.runtime import YomaEmbeddedRuntime


class FakeIntegrationAdapter(YomaAdapter):
    name = "central_server"
    category = "identity"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return ["test"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False


def make_persistence(tmp_path: Path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)
    return IntegrationPersistence(db_path)


def test_embedded_runtime_restores_integrations_on_start(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.configure({
        "system_number": "SYS001",
    })

    persistence.save(integration)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    assert runtime.status().integration_count == 0

    runtime.start()

    assert runtime.status().integration_count == 1
    assert runtime.integration_runtime.get(
        "central_server"
    ).configured is True

    runtime.stop()


def test_embedded_runtime_restores_configuration(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.configure({
        "endpoint": "https://central.example",
        "system_number": "SYS001",
    })

    persistence.save(integration)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    restored = runtime.integration_runtime.get(
        "central_server"
    )

    assert restored.configuration()["endpoint"] == (
        "https://central.example"
    )
    assert restored.configuration()["system_number"] == "SYS001"

    runtime.stop()


def test_embedded_runtime_does_not_auto_connect(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.configure({
        "endpoint": "https://central.example",
    })

    integration.set_connected(
        True,
        health={"status": "connected"},
    )

    persistence.save(integration)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    restored = runtime.integration_runtime.get(
        "central_server"
    )

    assert restored.connected is False

    runtime.stop()


def test_embedded_runtime_restores_disabled_integration(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.set_enabled(False)
    persistence.save(integration)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    restored = runtime.integration_runtime.get(
        "central_server"
    )

    assert restored.enabled is False

    runtime.stop()


def test_embedded_runtime_restore_is_idempotent(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    persistence.save(integration)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    first = runtime.restore_integrations()
    second = runtime.restore_integrations()

    assert len(first) == 1
    assert len(second) == 0
    assert runtime.status().integration_count == 1


def test_embedded_runtime_accepts_existing_integration_runtime():
    manager = IntegrationRuntimeManager()

    runtime = YomaEmbeddedRuntime(
        integration_runtime=manager,
    )

    assert runtime.integration_runtime is manager
