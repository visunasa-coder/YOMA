from yoma.office.central_server import CentralServerAdapter
from yoma.office.identity import IdentityRegistryManager


def make_manager():
    adapter = CentralServerAdapter(
        name="company-central-server",
    )

    return IdentityRegistryManager(adapter)


def test_manager_uses_central_server_provider():
    manager = make_manager()

    assert manager.provider == "company-central-server"


def test_manager_reports_unconfigured_central_server():
    manager = make_manager()

    health = manager.health()

    assert health["status"] == "unconfigured"
    assert health["provider"] == "company-central-server"


def test_manager_status_reports_unhealthy_when_unconfigured():
    manager = make_manager()

    status = manager.status()

    assert status.adapter == "company-central-server"
    assert status.healthy is False


def test_manager_lists_no_users_before_connection():
    manager = make_manager()

    assert manager.list_users() == []


def test_manager_lists_no_systems_before_connection():
    manager = make_manager()

    assert manager.list_systems() == []


def test_manager_unknown_user_returns_none():
    manager = make_manager()

    assert manager.get_user("EMP001") is None


def test_manager_unknown_external_user_returns_none():
    manager = make_manager()

    assert manager.resolve_user("EMP001") is None


def test_manager_unknown_system_returns_none():
    manager = make_manager()

    assert manager.get_system("SYS001") is None


def test_manager_can_use_configured_central_server():
    manager = make_manager()

    manager.adapter.configure(
        {
            "endpoint": "central-server",
            "protocol": "custom",
        }
    )

    health = manager.health()

    assert health["status"] == "disconnected"
    assert health["provider"] == "company-central-server"
