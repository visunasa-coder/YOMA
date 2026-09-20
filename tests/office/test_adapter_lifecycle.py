import pytest

from yoma.office.adapters.base import YomaAdapter


class LifecycleAdapter(YomaAdapter):
    name = "lifecycle_test"
    category = "test"

    def health(self):
        return {
            "status": "healthy",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["test"]

    def connect(self, config):
        self.configure(config)
        self._connected = True

    def disconnect(self):
        self._connected = False


def test_adapter_starts_unconfigured():
    adapter = LifecycleAdapter()

    assert adapter.configured is False
    assert adapter.connected is False


def test_adapter_configuration():
    adapter = LifecycleAdapter()

    adapter.configure({
        "endpoint": "http://example.local",
    })

    assert adapter.configured is True
    assert adapter.connected is False


def test_adapter_rejects_invalid_configuration():
    adapter = LifecycleAdapter()

    with pytest.raises(TypeError):
        adapter.configure(None)


def test_adapter_connection_lifecycle():
    adapter = LifecycleAdapter()

    adapter.connect({
        "endpoint": "http://example.local",
    })

    assert adapter.configured is True
    assert adapter.connected is True

    adapter.disconnect()

    assert adapter.connected is False


def test_metadata_is_safe():
    adapter = LifecycleAdapter()

    adapter.configure({
        "endpoint": "http://example.local",
    })

    metadata = adapter.metadata()

    assert metadata["name"] == "lifecycle_test"
    assert metadata["category"] == "test"
    assert metadata["configured"] is True
    assert metadata["connected"] is False
    assert "endpoint" not in metadata
    assert "password" not in metadata
    assert "token" not in metadata
