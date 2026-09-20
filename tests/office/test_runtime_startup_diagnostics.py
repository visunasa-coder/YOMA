from yoma.db import initialize
from yoma.office.runtime_state import RuntimeStatePersistence


def test_startup_diagnostics_exist_without_previous_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)

    diagnostics = state.startup_diagnostics()

    assert diagnostics["recovery_required"] is False
    assert diagnostics["previous_state"] is None
    assert diagnostics["message"]


def test_startup_diagnostics_detect_unclean_running_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="startup_complete")

    diagnostics = state.startup_diagnostics()

    assert diagnostics["recovery_required"] is True
    assert diagnostics["previous_state"] == "running"
    assert diagnostics["message"]


def test_startup_diagnostics_detect_failed_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="failed", reason="runtime_failure")

    diagnostics = state.startup_diagnostics()

    assert diagnostics["recovery_required"] is True
    assert diagnostics["previous_state"] == "failed"
    assert diagnostics["previous_reason"] == "runtime_failure"


def test_startup_diagnostics_clean_shutdown(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="stopped", reason="shutdown_complete")

    diagnostics = state.startup_diagnostics()

    assert diagnostics["recovery_required"] is False
    assert diagnostics["previous_state"] == "stopped"


def test_startup_diagnostics_contains_timestamp(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="failed", reason="crash")

    diagnostics = state.startup_diagnostics()

    assert diagnostics["previous_updated_at"]


def test_startup_diagnostics_preserves_recovery_reason(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    state = RuntimeStatePersistence(db_path)
    state.save(state="running", reason="startup_complete")

    diagnostics = state.startup_diagnostics()

    assert diagnostics["previous_reason"] == "startup_complete"
    assert "recovery" in diagnostics["message"].lower()
