from yoma.db import initialize
from yoma.office.runtime_state import RuntimeStatePersistence


def test_runtime_state_persistence_starts_empty(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = RuntimeStatePersistence(db_path)

    assert persistence.load() is None


def test_runtime_state_can_be_saved(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = RuntimeStatePersistence(db_path)

    persistence.save(
        state="running",
        reason="startup_complete",
    )

    record = persistence.load()

    assert record is not None
    assert record["state"] == "running"
    assert record["reason"] == "startup_complete"


def test_runtime_state_save_overwrites_current_state(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = RuntimeStatePersistence(db_path)

    persistence.save(state="booting", reason="startup")
    persistence.save(state="running", reason="startup_complete")

    record = persistence.load()

    assert record["state"] == "running"
    assert record["reason"] == "startup_complete"


def test_runtime_state_contains_timestamp(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = RuntimeStatePersistence(db_path)

    persistence.save(
        state="running",
        reason="startup_complete",
    )

    record = persistence.load()

    assert record["updated_at"]


def test_runtime_state_can_be_cleared(tmp_path):
    db_path = tmp_path / "yoma.db"
    initialize(db_path)

    persistence = RuntimeStatePersistence(db_path)

    persistence.save(
        state="running",
        reason="startup_complete",
    )

    persistence.clear()

    assert persistence.load() is None


def test_runtime_state_persistence_is_independent_per_database(tmp_path):
    db1 = tmp_path / "one.db"
    db2 = tmp_path / "two.db"

    initialize(db1)
    initialize(db2)

    first = RuntimeStatePersistence(db1)
    second = RuntimeStatePersistence(db2)

    first.save(state="running", reason="first")

    assert first.load()["state"] == "running"
    assert second.load() is None
