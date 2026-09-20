import pytest

from yoma.office.central_server import CentralServerAdapter


def make_adapter():
    return CentralServerAdapter(
        name="company-central-server",
    )


def test_adapter_has_identity():
    adapter = make_adapter()

    assert adapter.name == "company-central-server"
    assert adapter.category == "identity_registry"


def test_adapter_starts_unconfigured():
    adapter = make_adapter()

    health = adapter.health()

    assert health["status"] == "unconfigured"


def test_adapter_can_configure_connection():
    adapter = make_adapter()

    adapter.configure(
        {
            "endpoint": "central-server",
            "protocol": "custom",
        }
    )

    assert adapter.configured is True


def test_adapter_configuration_does_not_expose_secrets():
    adapter = make_adapter()

    adapter.configure(
        {
            "endpoint": "central-server",
            "protocol": "custom",
            "api_key": "super-secret",
        }
    )

    configuration = adapter.configuration()

    assert configuration["endpoint"] == "central-server"
    assert configuration["protocol"] == "custom"
    assert "api_key" not in configuration


def test_adapter_reports_disconnected_before_connection():
    adapter = make_adapter()

    assert adapter.connected is False


def test_adapter_rejects_invalid_configuration():
    adapter = make_adapter()

    with pytest.raises(TypeError):
        adapter.configure("invalid")


def test_adapter_users_are_empty_before_connection():
    adapter = make_adapter()

    assert adapter.list_users() == []


def test_adapter_systems_are_empty_before_connection():
    adapter = make_adapter()

    assert adapter.list_systems() == []


def test_adapter_unknown_user_returns_none():
    adapter = make_adapter()

    assert adapter.get_user("UNKNOWN") is None


def test_adapter_unknown_system_returns_none():
    adapter = make_adapter()

    assert adapter.get_system("UNKNOWN") is None
