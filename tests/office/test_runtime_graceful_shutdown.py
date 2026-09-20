from yoma.office.integration import Integration
from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.adapters.base import YomaAdapter


class FakeAdapter(YomaAdapter):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.category = "identity"

    def capabilities(self):
        return []

    def health(self):
        return {"status": "healthy"}

    def connect(self, config):
        return True

    def disconnect(self):
        return None


def test_shutdown_does_not_remove_registered_integrations():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    integration = Integration(
        "central_server",
        "company",
        "identity",
    )

    adapter = FakeAdapter("central_server")

    runtime.integration_runtime.register(integration, adapter)

    assert runtime.status().integration_count == 1

    runtime.start()
    runtime.stop()

    assert runtime.status().integration_count == 1
