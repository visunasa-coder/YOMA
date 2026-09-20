from pathlib import Path

from yoma.db import initialize
from yoma.office.integration import Integration
from yoma.office.integration.persistence import IntegrationPersistence


def make_store(tmp_path: Path):
    db_path = tmp_path / "yoma-test.db"
    initialize(db_path)
    return IntegrationPersistence(db_path)


def test_save_and_load(tmp_path):
    store = make_store(tmp_path)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.configure({
        "endpoint": "https://central.example",
        "system_number": "SYS001",
    })

    store.save(integration)

    records = store.load_all()

    assert len(records) == 1
    assert records[0]["name"] == "central_server"
    assert records[0]["provider"] == "company"
    assert records[0]["category"] == "identity"
    assert records[0]["enabled"] is True
    assert records[0]["configured"] is True
    assert records[0]["configuration"]["system_number"] == "SYS001"


def test_save_updates_existing_integration(tmp_path):
    store = make_store(tmp_path)

    integration = Integration(
        "google_workspace",
        "google",
        "workspace",
    )

    store.save(integration)

    integration.configure({
        "tenant": "production",
    })

    store.save(integration)

    records = store.load_all()

    assert len(records) == 1
    assert records[0]["configuration"]["tenant"] == "production"


def test_multiple_integrations_are_persistent(tmp_path):
    store = make_store(tmp_path)

    store.save(
        Integration(
            "google_workspace",
            "google",
            "workspace",
        )
    )

    store.save(
        Integration(
            "central_server",
            "company",
            "identity",
        )
    )

    records = store.load_all()

    assert len(records) == 2
    assert [item["name"] for item in records] == [
        "central_server",
        "google_workspace",
    ]


def test_delete(tmp_path):
    store = make_store(tmp_path)

    store.save(
        Integration(
            "attendance",
            "company",
            "attendance",
        )
    )

    assert store.delete("attendance") is True
    assert store.delete("attendance") is False
    assert store.load_all() == []


def test_disabled_state_persists(tmp_path):
    store = make_store(tmp_path)

    integration = Integration(
        "attendance",
        "company",
        "attendance",
    )

    integration.set_enabled(False)

    store.save(integration)

    record = store.load_all()[0]

    assert record["enabled"] is False
    assert record["status"] == "disabled"


def test_connection_state_status_persists(tmp_path):
    store = make_store(tmp_path)

    integration = Integration(
        "google_workspace",
        "google",
        "workspace",
    )

    integration.set_connected(
        True,
        health={"status": "healthy"},
    )

    store.save(integration)

    record = store.load_all()[0]

    assert record["status"] == "healthy"
