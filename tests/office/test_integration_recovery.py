from pathlib import Path

from yoma.db import connection_scope, initialize
from yoma.office.integration import (
    Integration,
    IntegrationPersistence,
    IntegrationRuntimeManager,
)
from yoma.office.runtime import YomaEmbeddedRuntime


def make_persistence(tmp_path: Path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)
    return IntegrationPersistence(db_path)


def test_restart_restores_multiple_integrations(tmp_path):
    persistence = make_persistence(tmp_path)

    first = Integration(
        "central_server",
        "company",
        "identity",
    )
    first.configure({"system_number": "SYS001"})

    second = Integration(
        "attendance",
        "company",
        "attendance",
    )
    second.configure({"device_id": "ATT001"})

    persistence.save(first)
    persistence.save(second)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    assert runtime.status().integration_count == 2
    assert runtime.integration_runtime.get(
        "central_server"
    ).configuration()["system_number"] == "SYS001"
    assert runtime.integration_runtime.get(
        "attendance"
    ).configuration()["device_id"] == "ATT001"

    runtime.stop()


def test_restart_preserves_disabled_state(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "attendance",
        "company",
        "attendance",
    )
    integration.set_enabled(False)
    persistence.save(integration)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    restored = runtime.integration_runtime.get("attendance")

    assert restored.enabled is False
    assert restored.connected is False

    runtime.stop()


def test_restart_never_auto_connects(tmp_path):
    persistence = make_persistence(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )
    integration.configure({"endpoint": "https://central.example"})
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


def test_runtime_start_stop_start_does_not_duplicate_integrations(
    tmp_path,
):
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

    runtime.start()
    runtime.stop()
    runtime.start()

    assert runtime.status().integration_count == 1

    runtime.stop()


def test_restore_survives_invalid_configuration_json(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = IntegrationPersistence(db_path)

    with connection_scope(db_path) as connection:
        connection.execute(
            """
            INSERT INTO yoma_integrations (
                integration_id,
                name,
                provider,
                category,
                enabled,
                configured,
                configuration_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "bad-config",
                "broken_integration",
                "company",
                "test",
                1,
                1,
                "{invalid-json",
                "configured",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        connection.commit()

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    restored = runtime.integration_runtime.get(
        "broken_integration"
    )

    assert restored.configured is True
    assert restored.configuration() == {}
    assert restored.connected is False

    runtime.stop()


def test_restore_is_safe_when_no_database_records_exist(tmp_path):
    persistence = make_persistence(tmp_path)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=persistence,
    )

    runtime.start()

    assert runtime.status().integration_count == 0

    runtime.stop()
