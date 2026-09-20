from datetime import datetime, timezone

from yoma.office.adapters import (
    AdapterRuntimeManager,
    YomaAdapter,
)
from yoma.office.operations import OperationalEvent


class LifecycleAdapter(YomaAdapter):
    name = "runtime_test"
    category = "test"

    def __init__(self):
        super().__init__()
        self.collect_count = 0

    def health(self):
        return {
            "status": "healthy" if self.connected else "disconnected",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["test_events"]

    def connect(self, config):
        self.configure(config)
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        if not self.connected:
            raise ConnectionError("not connected")

        self.collect_count += 1

        return [
            OperationalEvent(
                event_id=f"EV-{self.collect_count}",
                event_type="test.event",
                occurred_at=datetime.now(timezone.utc),
                source=self.name,
            )
        ]


class FailingAdapter(YomaAdapter):
    name = "failing_runtime_test"
    category = "test"

    def health(self):
        return {
            "status": "healthy",
            "connected": True,
        }

    def capabilities(self):
        return ["test"]

    def connect(self, config):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        raise RuntimeError("simulated failure")


def test_manager_registers_adapter():
    manager = AdapterRuntimeManager()

    adapter = LifecycleAdapter()

    manager.register(adapter)

    assert len(manager.registry) == 1


def test_manager_configures_adapter():
    manager = AdapterRuntimeManager()

    adapter = LifecycleAdapter()
    manager.register(adapter)

    manager.configure(
        "runtime_test",
        {"endpoint": "http://example.local"},
    )

    assert adapter.configured is True
    assert adapter.connected is False


def test_manager_connects_adapter():
    manager = AdapterRuntimeManager()

    manager.register(LifecycleAdapter())

    result = manager.connect(
        "runtime_test",
        {"endpoint": "http://example.local"},
    )

    assert result.status == "connected"
    assert result.adapter == "runtime_test"


def test_manager_collects_events():
    manager = AdapterRuntimeManager()

    manager.register(LifecycleAdapter())

    manager.connect("runtime_test", {})

    events, result = manager.collect("runtime_test")

    assert result.status == "collected"
    assert result.events_collected == 1
    assert events[0].event_type == "test.event"


def test_manager_collects_all_adapters():
    manager = AdapterRuntimeManager()

    first = LifecycleAdapter()
    manager.register(first)

    manager.connect("runtime_test", {})

    events, results = manager.collect_all()

    assert len(events) == 1
    assert len(results) == 1
    assert results[0].status == "collected"


def test_failed_adapter_does_not_crash_collect_all():
    manager = AdapterRuntimeManager()

    good = LifecycleAdapter()
    bad = FailingAdapter()

    manager.register(good)
    manager.register(bad)

    manager.connect("runtime_test", {})

    events, results = manager.collect_all()

    assert len(events) == 1

    result_map = {
        result.adapter: result
        for result in results
    }

    assert result_map["runtime_test"].status == "collected"
    assert result_map["failing_runtime_test"].status == "failed"
    assert result_map["failing_runtime_test"].error == "RuntimeError"


def test_manager_disconnects_adapter():
    manager = AdapterRuntimeManager()

    adapter = LifecycleAdapter()
    manager.register(adapter)

    manager.connect("runtime_test", {})

    assert adapter.connected is True

    manager.disconnect("runtime_test")

    assert adapter.connected is False


def test_manager_status_is_safe():
    manager = AdapterRuntimeManager()

    adapter = LifecycleAdapter()
    manager.register(adapter)

    manager.configure(
        "runtime_test",
        {"token": "SECRET"},
    )

    status = manager.status()

    assert len(status) == 1
    assert status[0]["name"] == "runtime_test"
    assert status[0]["configured"] is True
    assert "token" not in status[0]
    assert "SECRET" not in str(status)


def test_disconnect_all_isolated():
    manager = AdapterRuntimeManager()

    first = LifecycleAdapter()
    second = LifecycleAdapter()

    first.name = "runtime_test_first"
    second.name = "runtime_test_second"

    manager.register(first)
    manager.register(second)

    manager.connect("runtime_test_first", {})
    manager.connect("runtime_test_second", {})

    manager.disconnect_all()

    assert first.connected is False
    assert second.connected is False
