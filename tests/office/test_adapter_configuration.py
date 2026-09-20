from yoma.office.adapters import YomaAdapter


class ConfigurationAdapter(YomaAdapter):
    name = "configuration_test"
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


def test_configuration_returns_copy():
    adapter = ConfigurationAdapter()

    adapter.configure({
        "endpoint": "http://example.local",
        "device": {
            "id": "DEVICE001",
        },
    })

    config = adapter.configuration()

    assert config["endpoint"] == "http://example.local"

    config["endpoint"] = "modified"

    assert adapter.configuration()["endpoint"] == "http://example.local"


def test_configuration_is_available_for_reconnect():
    adapter = ConfigurationAdapter()

    adapter.connect({
        "endpoint": "http://example.local",
    })

    adapter.disconnect()

    adapter.connect(adapter.configuration())

    assert adapter.connected is True
    assert adapter.configuration()["endpoint"] == "http://example.local"
