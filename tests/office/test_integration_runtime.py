from datetime import datetime, timezone

import pytest

from yoma.office.adapters import YomaAdapter
from yoma.office.integration import (
    Integration,
    IntegrationRuntimeManager,
)


class RuntimeTestAdapter(YomaAdapter):
    name = "runtime_test"
    category = "test"

    def __init__(self):
        super().__init__()
        self.connect_count = 0
        self.disconnect_count = 0

    def health(self):
        return {
            "status": "healthy",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["test_events"]

    def connect(self, config):
        self.connect_count += 1
        self._connected = True

    def disconnect(self):
        self.disconnect_count += 1
        self._connected = False

    def collect_events(self):
        if not self.connected:
            raise RuntimeError("not connected")

        from yoma.office.operations import OperationalEvent

        return [
            OperationalEvent(
                event_id="RUNTIME-EVENT-1",
                event_type="test.runtime",
                occurred_at=datetime.now(timezone.utc),
                source=self.name,
            )
        ]


def make_runtime():
    manager = IntegrationRuntimeManager()

    integration = Integration(
        "runtime_test",
        "test_provider",
        "test",
    )

    adapter = RuntimeTestAdapter()

    manager.register(integration, adapter)

    return manager, integration, adapter


def test_register_requires_matching_names():
    manager = IntegrationRuntimeManager()

    integration = Integration(
        "integration_one",
        "test",
        "test",
    )

    adapter = RuntimeTestAdapter()

    with pytest.raises(ValueError):
        manager.register(integration, adapter)


def test_configure_updates_both_layers():
    manager, integration, adapter = make_runtime()

    config = {
        "endpoint": "http://localhost",
        "system": "TEST",
    }

    manager.configure("runtime_test", config)

    assert integration.configured is True
    assert adapter.configured is True
    assert adapter.configuration() == config


def test_connect_requires_configuration():
    manager, _, _ = make_runtime()

    with pytest.raises(RuntimeError, match="not configured"):
        manager.connect("runtime_test")


def test_connect_updates_integration_state():
    manager, integration, adapter = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    result = manager.connect("runtime_test")

    assert result.status == "connected"
    assert integration.connected is True
    assert adapter.connected is True
    assert adapter.connect_count == 1


def test_disabled_integration_cannot_connect():
    manager, integration, _ = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    manager.disable("runtime_test")

    assert integration.enabled is False

    with pytest.raises(RuntimeError, match="disabled"):
        manager.connect("runtime_test")


def test_enable_reenables_integration():
    manager, integration, _ = make_runtime()

    manager.disable("runtime_test")
    manager.enable("runtime_test")

    assert integration.enabled is True


def test_disconnect_updates_integration_state():
    manager, integration, adapter = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    manager.connect("runtime_test")
    manager.disconnect("runtime_test")

    assert integration.connected is False
    assert adapter.connected is False
    assert adapter.disconnect_count == 1


def test_collect_requires_connection():
    manager, _, _ = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    with pytest.raises(RuntimeError, match="not connected"):
        manager.collect("runtime_test")


def test_collect_delegates_to_adapter_runtime():
    manager, _, _ = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    manager.connect("runtime_test")

    events, result = manager.collect("runtime_test")

    assert result.status == "collected"
    assert result.events_collected == 1
    assert len(events) == 1
    assert events[0].event_type == "test.runtime"


def test_disable_disconnects_connected_integration():
    manager, integration, adapter = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    manager.connect("runtime_test")
    manager.disable("runtime_test")

    assert integration.enabled is False
    assert integration.connected is False
    assert adapter.connected is False
    assert adapter.disconnect_count == 1


def test_health_delegates_to_adapter():
    manager, _, _ = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    manager.connect("runtime_test")

    health = manager.health("runtime_test")

    assert health["status"] == "healthy"


def test_status_contains_integration_state():
    manager, _, _ = make_runtime()

    manager.configure(
        "runtime_test",
        {"endpoint": "http://localhost"},
    )

    status = manager.status()

    assert len(status) == 1
    assert status[0]["name"] == "runtime_test"
    assert status[0]["provider"] == "test_provider"
    assert status[0]["configured"] is True
    assert status[0]["connected"] is False


def test_unregister_removes_integration_and_adapter():
    manager, _, _ = make_runtime()

    assert manager.unregister("runtime_test") is True
    assert manager.unregister("runtime_test") is False
    assert manager.status() == []
