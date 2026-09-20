from datetime import datetime, timezone

from yoma.office.adapters.base import YomaAdapter
from yoma.office.adapters.registry import AdapterRegistry
from yoma.office.operations import OperationalEvent


class TestAdapter(YomaAdapter):
    name = "test_adapter"
    category = "test"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return [
            "test.read",
            "test.events",
        ]

    def connect(self, config):
        self.config = config

    def disconnect(self):
        self.config = None

    def collect_events(self):
        return [
            OperationalEvent(
                event_id="EV001",
                event_type="test.event",
                occurred_at=datetime.now(timezone.utc),
                source=self.name,
            )
        ]


def test_adapter_capability_contract():
    adapter = TestAdapter()

    assert adapter.supports("test.read")
    assert adapter.supports("test.events")
    assert not adapter.supports("test.write")


def test_adapter_metadata():
    adapter = TestAdapter()

    metadata = adapter.metadata()

    assert metadata["name"] == "test_adapter"
    assert metadata["category"] == "test"
    assert "test.read" in metadata["capabilities"]


def test_registry_register_and_get():
    registry = AdapterRegistry()
    adapter = TestAdapter()

    registry.register(adapter)

    assert len(registry) == 1
    assert registry.get("test_adapter") is adapter


def test_registry_require():
    registry = AdapterRegistry()
    registry.register(TestAdapter())

    assert registry.require("test_adapter").name == "test_adapter"


def test_registry_require_missing():
    registry = AdapterRegistry()

    try:
        registry.require("missing")
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_registry_category_filter():
    registry = AdapterRegistry()

    registry.register(TestAdapter())

    assert len(registry.by_category("test")) == 1
    assert len(registry.by_category("email")) == 0


def test_registry_capability_filter():
    registry = AdapterRegistry()

    registry.register(TestAdapter())

    assert len(registry.capability("test.read")) == 1
    assert len(registry.capability("test.write")) == 0


def test_registry_collects_normalized_events():
    registry = AdapterRegistry()

    registry.register(TestAdapter())

    events = registry.collect_events()

    assert len(events) == 1
    assert isinstance(events[0], OperationalEvent)
    assert events[0].source == "test_adapter"


def test_registry_unregister():
    registry = AdapterRegistry()

    registry.register(TestAdapter())

    assert registry.unregister("test_adapter") is True
    assert registry.unregister("test_adapter") is False
    assert len(registry) == 0


def test_duplicate_adapter_is_rejected():
    registry = AdapterRegistry()

    registry.register(TestAdapter())

    try:
        registry.register(TestAdapter())
        assert False, "Expected ValueError"
    except ValueError:
        pass
