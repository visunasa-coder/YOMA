import json
from pathlib import Path

import pytest

from yoma.office.licensing.activation import ActivationStatus
from yoma.office.licensing.persistence import (
    LicensePersistence,
    PersistedActivation,
)


def make_state(**overrides):
    values = {
        "license_id": "LIC-001",
        "organization_id": "ORG-001",
        "status": ActivationStatus.ACTIVE,
        "activated_at": "2026-06-01T10:00:00+00:00",
    }
    values.update(overrides)
    return PersistedActivation(**values)


def test_missing_state_returns_none(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    assert persistence.load() is None


def test_state_can_be_saved_and_loaded(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")
    state = make_state()

    persistence.save(state)

    assert persistence.load() == state


def test_saved_file_exists(tmp_path):
    path = tmp_path / "license.json"
    persistence = LicensePersistence(path)

    persistence.save(make_state())

    assert path.exists()


def test_saved_json_is_deterministic(tmp_path):
    path = tmp_path / "license.json"
    persistence = LicensePersistence(path)

    persistence.save(make_state())

    first = path.read_text(encoding="utf-8")

    persistence.save(make_state())

    second = path.read_text(encoding="utf-8")

    assert first == second


def test_saved_json_is_valid(tmp_path):
    path = tmp_path / "license.json"
    persistence = LicensePersistence(path)

    persistence.save(make_state())

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["license_id"] == "LIC-001"
    assert payload["organization_id"] == "ORG-001"
    assert payload["status"] == "active"


def test_deactivated_state_can_be_persisted(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")
    state = make_state(
        status=ActivationStatus.DEACTIVATED,
        activated_at=None,
    )

    persistence.save(state)

    assert persistence.load() == state


def test_inactive_state_can_be_persisted(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")
    state = make_state(
        status=ActivationStatus.INACTIVE,
        activated_at=None,
    )

    persistence.save(state)

    assert persistence.load() == state


def test_corrupt_json_returns_none(tmp_path):
    path = tmp_path / "license.json"
    path.write_text("{invalid", encoding="utf-8")

    persistence = LicensePersistence(path)

    assert persistence.load() is None


def test_non_object_json_returns_none(tmp_path):
    path = tmp_path / "license.json"
    path.write_text("[]", encoding="utf-8")

    persistence = LicensePersistence(path)

    assert persistence.load() is None


def test_missing_license_id_returns_none(tmp_path):
    path = tmp_path / "license.json"
    path.write_text(
        json.dumps(
            {
                "organization_id": "ORG-001",
                "status": "active",
                "activated_at": None,
            }
        ),
        encoding="utf-8",
    )

    assert LicensePersistence(path).load() is None


def test_missing_organization_id_returns_none(tmp_path):
    path = tmp_path / "license.json"
    path.write_text(
        json.dumps(
            {
                "license_id": "LIC-001",
                "status": "active",
                "activated_at": None,
            }
        ),
        encoding="utf-8",
    )

    assert LicensePersistence(path).load() is None


def test_invalid_status_returns_none(tmp_path):
    path = tmp_path / "license.json"
    path.write_text(
        json.dumps(
            {
                "license_id": "LIC-001",
                "organization_id": "ORG-001",
                "status": "unknown",
                "activated_at": None,
            }
        ),
        encoding="utf-8",
    )

    assert LicensePersistence(path).load() is None


def test_invalid_activated_at_type_returns_none(tmp_path):
    path = tmp_path / "license.json"
    path.write_text(
        json.dumps(
            {
                "license_id": "LIC-001",
                "organization_id": "ORG-001",
                "status": "active",
                "activated_at": 123,
            }
        ),
        encoding="utf-8",
    )

    assert LicensePersistence(path).load() is None


def test_clear_removes_state(tmp_path):
    path = tmp_path / "license.json"
    persistence = LicensePersistence(path)

    persistence.save(make_state())
    persistence.clear()

    assert persistence.load() is None
    assert not path.exists()


def test_clear_is_safe_when_state_is_missing(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    persistence.clear()

    assert persistence.load() is None


def test_persistence_path_is_exposed(tmp_path):
    path = tmp_path / "license.json"
    persistence = LicensePersistence(path)

    assert persistence.path == Path(path)


def test_persisted_activation_is_immutable():
    state = make_state()

    with pytest.raises(AttributeError):
        state.license_id = "LIC-002"


def test_invalid_state_type_is_rejected(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    with pytest.raises(
        TypeError,
        match="state must be a PersistedActivation",
    ):
        persistence.save("invalid")


def test_parent_directory_is_created(tmp_path):
    path = tmp_path / "nested" / "state" / "license.json"
    persistence = LicensePersistence(path)

    persistence.save(make_state())

    assert path.exists()


def test_persistence_does_not_create_execution_authority(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")
    state = make_state()

    persistence.save(state)
    restored = persistence.load()

    assert restored is not None
    assert not hasattr(restored, "execute")
    assert not hasattr(restored, "executable")
    assert not hasattr(restored, "authorized")
