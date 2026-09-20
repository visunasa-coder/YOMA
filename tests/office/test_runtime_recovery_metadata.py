from yoma.db import initialize
from yoma.office.runtime_state import RuntimeStatePersistence


def test_no_recovery_required_without_previous_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    recovery = state.recovery_metadata()

    assert recovery["recovery_required"] is False


def test_running_previous_state_requires_recovery(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="startup_complete")

    recovery = state.recovery_metadata()

    assert recovery["recovery_required"] is True
    assert recovery["previous_state"] == "running"


def test_stopped_previous_state_does_not_require_recovery(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="stopped", reason="shutdown_complete")

    recovery = state.recovery_metadata()

    assert recovery["recovery_required"] is False
    assert recovery["previous_state"] == "stopped"


def test_failed_previous_state_requires_recovery(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="failed", reason="runtime_failure")

    recovery = state.recovery_metadata()

    assert recovery["recovery_required"] is True
    assert recovery["previous_state"] == "failed"
    assert recovery["previous_reason"] == "runtime_failure"


def test_recovery_metadata_contains_previous_timestamp(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="startup_complete")

    recovery = state.recovery_metadata()

    assert recovery["previous_updated_at"]


def test_clean_shutdown_metadata_is_not_recovery(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    state.save(state="running", reason="startup_complete")
    state.save(state="stopping", reason="shutdown_begin")
    state.save(state="stopped", reason="shutdown_complete")

    recovery = state.recovery_metadata()

    assert recovery["recovery_required"] is False
    assert recovery["previous_state"] == "stopped"
