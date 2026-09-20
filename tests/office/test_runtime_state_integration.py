from yoma.db import initialize
from yoma.office.integration import IntegrationPersistence
from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.runtime_state import RuntimeStatePersistence


def test_start_persists_running_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )

    runtime.start()

    record = state.load()

    assert record is not None
    assert record["state"] == "running"

    runtime.stop()


def test_stop_persists_stopped_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )

    runtime.start()
    runtime.stop()

    record = state.load()

    assert record is not None
    assert record["state"] == "stopped"


def test_start_persistence_contains_reason(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )

    runtime.start()

    record = state.load()

    assert record is not None
    assert record["reason"]

    runtime.stop()


def test_failed_start_persists_failed_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    class FailingRuntime(YomaEmbeddedRuntime):
        def restore_integrations(self):
            raise RuntimeError("startup failure")

    runtime = FailingRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )

    import pytest

    with pytest.raises(RuntimeError):
        runtime.start()

    record = state.load()

    assert record is not None
    assert record["state"] == "failed"
    assert record["reason"]


def test_runtime_state_persistence_uses_same_database(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )

    runtime.start()
    runtime.stop()

    assert state.load()["state"] == "stopped"


def test_persisted_state_updates_after_restart_cycle(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime = YomaEmbeddedRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )

    runtime.start()
    assert state.load()["state"] == "running"

    runtime.stop()
    assert state.load()["state"] == "stopped"

    runtime.start()
    assert state.load()["state"] == "running"

    runtime.stop()
