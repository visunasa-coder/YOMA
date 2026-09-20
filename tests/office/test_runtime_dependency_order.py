from pathlib import Path

from yoma.db import initialize
from yoma.office.integration import (
    Integration,
    IntegrationPersistence,
)
from yoma.office.runtime import YomaEmbeddedRuntime


def test_scheduler_is_not_running_before_runtime_start():
    runtime = YomaEmbeddedRuntime(
        collection_interval=3600,
    )

    assert runtime.status().scheduler_running is False
    assert runtime.running is False


def test_scheduler_starts_only_after_runtime_becomes_running():
    runtime = YomaEmbeddedRuntime(
        collection_interval=3600,
    )

    assert runtime.running is False
    assert runtime.status().scheduler_running is False

    runtime.start()

    assert runtime.running is True
    assert runtime.status().scheduler_running is True

    runtime.stop()


def test_integrations_are_restored_before_scheduler_starts(
    tmp_path,
):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = IntegrationPersistence(db_path)

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
        collection_interval=3600,
    )

    assert runtime.status().integration_count == 0
    assert runtime.status().scheduler_running is False

    runtime.start()

    assert runtime.status().integration_count == 1
    assert runtime.running is True
    assert runtime.status().scheduler_running is True

    runtime.stop()


def test_scheduler_cannot_collect_before_runtime_start():
    runtime = YomaEmbeddedRuntime(
        collection_interval=3600,
    )

    assert runtime.running is False
    assert runtime.status().scheduler_running is False


def test_runtime_start_preserves_component_identity():
    runtime = YomaEmbeddedRuntime()

    bus = runtime.bus
    adapters = runtime.adapters
    scheduler = runtime.scheduler
    intelligence = runtime.intelligence
    decisions = runtime.decisions

    runtime.start()

    assert runtime.bus is bus
    assert runtime.adapters is adapters
    assert runtime.scheduler is scheduler
    assert runtime.intelligence is intelligence
    assert runtime.decisions is decisions

    runtime.stop()


def test_runtime_start_does_not_replace_core_components():
    runtime = YomaEmbeddedRuntime()

    original = {
        "bus": runtime.bus,
        "adapters": runtime.adapters,
        "scheduler": runtime.scheduler,
        "intelligence": runtime.intelligence,
        "decisions": runtime.decisions,
    }

    runtime.start()

    assert runtime.bus is original["bus"]
    assert runtime.adapters is original["adapters"]
    assert runtime.scheduler is original["scheduler"]
    assert runtime.intelligence is original["intelligence"]
    assert runtime.decisions is original["decisions"]

    runtime.stop()


def test_runtime_stop_leaves_components_available():
    runtime = YomaEmbeddedRuntime()

    runtime.start()
    runtime.stop()

    assert runtime.bus is not None
    assert runtime.adapters is not None
    assert runtime.scheduler is not None
    assert runtime.intelligence is not None
    assert runtime.decisions is not None
