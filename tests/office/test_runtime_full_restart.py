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


def test_full_clean_restart_cycle(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime1 = make_runtime(db_path, state)
    runtime1.start()

    assert runtime1.running is True
    assert state.load()["state"] == "running"

    runtime1.stop()

    assert runtime1.running is False
    assert state.load()["state"] == "stopped"

    runtime2 = make_runtime(db_path, state)

    assert runtime2.running is False
    assert runtime2.status().runtime_state == "stopped"

    runtime2.start()

    assert runtime2.running is True
    assert state.load()["state"] == "running"

    runtime2.stop()


def test_full_unclean_restart_detection(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="startup_complete")

    runtime = make_runtime(db_path, state)

    assert runtime.running is False

    diagnostics = state.startup_diagnostics()

    assert diagnostics["recovery_required"] is True
    assert diagnostics["previous_state"] == "running"


def test_failed_runtime_is_detected_after_restart(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="failed", reason="runtime_failure")

    runtime = make_runtime(db_path, state)

    diagnostics = state.startup_diagnostics()

    assert diagnostics["recovery_required"] is True
    assert diagnostics["previous_state"] == "failed"
    assert diagnostics["previous_reason"] == "runtime_failure"


def test_successful_restart_clears_recovery_condition(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="previous_process_running")

    runtime = make_runtime(db_path, state)

    assert state.startup_diagnostics()["recovery_required"] is True

    runtime.start()

    assert runtime.running is True
    assert state.load()["state"] == "running"

    runtime.stop()

    assert state.load()["state"] == "stopped"
    assert state.startup_diagnostics()["recovery_required"] is False


def test_restart_preserves_lifecycle_history(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime = make_runtime(db_path, state)

    runtime.start()
    runtime.stop()

    history = state.history()

    assert [item["state"] for item in history] == [
        "booting",
        "running",
        "stopping",
        "stopped",
    ]


def test_second_runtime_can_complete_full_restart(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    runtime1 = make_runtime(db_path, state)
    runtime1.start()
    runtime1.stop()

    runtime2 = make_runtime(db_path, state)
    runtime2.start()

    assert runtime2.status().runtime_state == "running"
    assert runtime2.running is True

    runtime2.stop()

    assert state.load()["state"] == "stopped"
