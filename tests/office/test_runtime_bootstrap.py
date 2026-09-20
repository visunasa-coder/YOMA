import pytest

from yoma.office.runtime import YomaEmbeddedRuntime


def test_runtime_initial_state_is_stopped():
    runtime = YomaEmbeddedRuntime()

    status = runtime.status()

    assert runtime.running is False
    assert status.running is False


def test_runtime_start_is_idempotent():
    runtime = YomaEmbeddedRuntime()

    runtime.start()
    runtime.start()

    assert runtime.running is True

    runtime.stop()


def test_runtime_stop_is_idempotent():
    runtime = YomaEmbeddedRuntime()

    runtime.start()
    runtime.stop()
    runtime.stop()

    assert runtime.running is False


def test_runtime_start_restores_integrations_before_running(
    tmp_path,
):
    from yoma.db import initialize
    from yoma.office.integration import Integration
    from yoma.office.integration import IntegrationPersistence

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
    )

    assert runtime.running is False
    assert runtime.status().integration_count == 0

    runtime.start()

    assert runtime.running is True
    assert runtime.status().integration_count == 1

    runtime.stop()


def test_runtime_does_not_start_scheduler_twice():
    runtime = YomaEmbeddedRuntime(
        collection_interval=3600,
    )

    runtime.start()

    first = runtime.status()
    runtime.start()
    second = runtime.status()

    assert first.scheduler_running is True
    assert second.scheduler_running is True
    assert second.scheduler_cycle_count >= first.scheduler_cycle_count

    runtime.stop()


def test_runtime_stop_stops_scheduler():
    runtime = YomaEmbeddedRuntime(
        collection_interval=3600,
    )

    runtime.start()

    assert runtime.status().scheduler_running is True

    runtime.stop()

    assert runtime.status().scheduler_running is False


def test_runtime_requires_running_for_operations():
    runtime = YomaEmbeddedRuntime()

    with pytest.raises(RuntimeError):
        runtime.collect_events()

    with pytest.raises(RuntimeError):
        runtime.publish(None)

    with pytest.raises(RuntimeError):
        runtime.analyze([])

    with pytest.raises(RuntimeError):
        runtime.decide([])
