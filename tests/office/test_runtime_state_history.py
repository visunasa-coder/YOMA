from yoma.db import initialize
from yoma.office.runtime_state import RuntimeStatePersistence


def test_runtime_state_history_starts_empty(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    assert state.history() == []


def test_save_records_lifecycle_history(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    state.save(state="booting", reason="startup_begin")

    history = state.history()

    assert len(history) == 1
    assert history[0]["state"] == "booting"
    assert history[0]["reason"] == "startup_begin"


def test_multiple_states_are_recorded_in_order(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    state.save(state="booting", reason="startup_begin")
    state.save(state="running", reason="startup_complete")
    state.save(state="stopping", reason="shutdown_begin")
    state.save(state="stopped", reason="shutdown_complete")

    history = state.history()

    assert [item["state"] for item in history] == [
        "booting",
        "running",
        "stopping",
        "stopped",
    ]


def test_current_state_remains_latest_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    state.save(state="running", reason="startup_complete")
    state.save(state="failed", reason="runtime_failure")

    assert state.load()["state"] == "failed"
    assert len(state.history()) == 2


def test_history_contains_timestamps(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    state.save(state="running", reason="startup_complete")

    record = state.history()[0]

    assert record["updated_at"]


def test_history_does_not_change_previous_records(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    state.save(state="running", reason="startup_complete")
    first = dict(state.history()[0])

    state.save(state="stopped", reason="shutdown_complete")

    history = state.history()

    assert history[0] == first
    assert history[1]["state"] == "stopped"
