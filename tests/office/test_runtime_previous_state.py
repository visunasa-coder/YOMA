from yoma.db import initialize
from yoma.office.integration import IntegrationPersistence
from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.runtime_state import RuntimeStatePersistence


def make_runtime(db_path, state):
    return YomaEmbeddedRuntime(
        integration_persistence=IntegrationPersistence(db_path),
        runtime_state_persistence=state,
        collection_interval=3600,
    )


def test_previous_running_state_can_be_loaded(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="previous_process_running")

    assert state.load()["state"] == "running"


def test_previous_stopped_state_can_be_loaded(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="stopped", reason="clean_shutdown")

    assert state.load()["state"] == "stopped"


def test_previous_failed_state_can_be_loaded(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="failed", reason="previous_startup_failure")

    assert state.load()["state"] == "failed"


def test_new_runtime_can_access_previous_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="previous_process_running")

    runtime = make_runtime(db_path, state)

    assert runtime.runtime_state_persistence is state
    assert runtime.runtime_state_persistence.load()["state"] == "running"


def test_previous_state_does_not_force_new_runtime_running(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="previous_process_running")

    runtime = make_runtime(db_path, state)

    assert runtime.running is False
    assert runtime.status().runtime_state == "stopped"


def test_previous_state_survives_new_runtime_instance(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="failed", reason="previous_crash")

    runtime = make_runtime(db_path, state)

    assert runtime.status().runtime_state == "stopped"
    assert state.load()["state"] == "failed"
    assert state.load()["reason"] == "previous_crash"
