import pytest

from yoma.office.integration import (
    Integration,
    IntegrationRegistry,
)


def test_integration_requires_name():
    with pytest.raises(ValueError):
        Integration("", "google", "workspace")


def test_integration_requires_provider():
    with pytest.raises(ValueError):
        Integration("google_workspace", "", "workspace")


def test_integration_requires_category():
    with pytest.raises(ValueError):
        Integration("google_workspace", "google", "")


def test_integration_initial_state():
    integration = Integration(
        "google_workspace",
        "google",
        "workspace",
    )

    assert integration.enabled is True
    assert integration.configured is False
    assert integration.connected is False
    assert integration.status().health["status"] == "unconfigured"


def test_integration_configuration_is_isolated():
    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    config = {
        "endpoint": "https://central.example",
        "system_number": "SYS001",
    }

    integration.configure(config)

    config["endpoint"] = "changed"

    assert (
        integration.configuration()["endpoint"]
        == "https://central.example"
    )


def test_integration_configuration_updates_state():
    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.configure({
        "endpoint": "https://central.example",
    })

    assert integration.configured is True
    assert integration.connected is False
    assert integration.status().health["status"] == "configured"


def test_integration_enable_disable():
    integration = Integration(
        "attendance",
        "company",
        "attendance",
    )

    integration.set_enabled(False)

    assert integration.enabled is False
    assert integration.connected is False
    assert integration.status().health["status"] == "disabled"

    integration.set_enabled(True)

    assert integration.enabled is True


def test_integration_connection_state():
    integration = Integration(
        "google_workspace",
        "google",
        "workspace",
    )

    integration.set_connected(
        True,
        health={"status": "healthy"},
    )

    assert integration.connected is True
    assert integration.status().health["status"] == "healthy"

    integration.set_connected(False)

    assert integration.connected is False
    assert integration.status().health["status"] == "disconnected"


def test_registry_register_and_lookup():
    registry = IntegrationRegistry()

    integration = Integration(
        "google_workspace",
        "google",
        "workspace",
    )

    registry.register(integration)

    assert len(registry) == 1
    assert registry.get("google_workspace") is integration
    assert registry.require("google_workspace") is integration


def test_registry_rejects_duplicate():
    registry = IntegrationRegistry()

    registry.register(
        Integration(
            "google_workspace",
            "google",
            "workspace",
        )
    )

    with pytest.raises(ValueError):
        registry.register(
            Integration(
                "google_workspace",
                "google",
                "workspace",
            )
        )


def test_registry_unregister():
    registry = IntegrationRegistry()

    registry.register(
        Integration(
            "attendance",
            "company",
            "attendance",
        )
    )

    assert registry.unregister("attendance") is True
    assert registry.unregister("attendance") is False
    assert len(registry) == 0


def test_registry_require_unknown_raises():
    registry = IntegrationRegistry()

    with pytest.raises(KeyError):
        registry.require("missing")


def test_registry_filters_provider():
    registry = IntegrationRegistry()

    registry.register(
        Integration("google_one", "google", "workspace")
    )
    registry.register(
        Integration("google_two", "google", "calendar")
    )
    registry.register(
        Integration("zoho_one", "zoho", "business")
    )

    results = registry.by_provider("google")

    assert len(results) == 2
    assert {item.name for item in results} == {
        "google_one",
        "google_two",
    }


def test_registry_filters_category():
    registry = IntegrationRegistry()

    registry.register(
        Integration("attendance_one", "company", "attendance")
    )
    registry.register(
        Integration("attendance_two", "vendor", "attendance")
    )
    registry.register(
        Integration("google_one", "google", "workspace")
    )

    results = registry.by_category("attendance")

    assert len(results) == 2


def test_registry_list_returns_status_metadata():
    registry = IntegrationRegistry()

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    integration.configure({
        "endpoint": "https://central.example",
    })

    registry.register(integration)

    items = registry.list()

    assert len(items) == 1
    assert items[0]["name"] == "central_server"
    assert items[0]["provider"] == "company"
    assert items[0]["category"] == "identity"
    assert items[0]["configured"] is True
    assert items[0]["connected"] is False
