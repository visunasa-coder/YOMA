from datetime import datetime, timezone

import pytest

from yoma.office.adapters.base import YomaAdapter
from yoma.office.identity import (
    IdentityRegistryAdapter,
    IdentityRegistryManager,
    UserIdentity,
)
from yoma.office.operations import OperationalEvent
from yoma.office.runtime import YomaEmbeddedRuntime


class TestIdentityAdapter(IdentityRegistryAdapter):
    name = "test_registry"

    def health(self):
        return {"status": "healthy"}

    def get_user(self, user_id):
        return UserIdentity(user_id=user_id, name="Test User")

    def list_users(self):
        return [UserIdentity(user_id="U1", name="Test User")]

    def get_system(self, system_id):
        return None

    def list_systems(self):
        return []

    def resolve_user(self, external_id):
        return self.get_user(external_id)


class TestAdapter(YomaAdapter):
    name = "test_adapter"
    category = "test"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return ["test_events"]

    def connect(self, config):
        pass

    def disconnect(self):
        pass

    def collect_events(self):
        return [
            OperationalEvent(
                event_id="EV1",
                event_type="test.event",
                occurred_at=datetime.now(timezone.utc),
                source=self.name,
            )
        ]


def test_runtime_starts_and_stops():
    runtime = YomaEmbeddedRuntime()

    assert runtime.running is False

    runtime.start()

    assert runtime.running is True

    runtime.stop()

    assert runtime.running is False


def test_runtime_status():
    identity = IdentityRegistryManager(TestIdentityAdapter())
    runtime = YomaEmbeddedRuntime(identity=identity)

    runtime.register_adapter(TestAdapter())
    runtime.start()

    status = runtime.status()

    assert status.running is True
    assert status.adapter_count == 1
    assert status.identity_provider == "test_registry"


def test_runtime_collects_adapter_events():
    runtime = YomaEmbeddedRuntime()
    runtime.register_adapter(TestAdapter())
    runtime.start()

    events = runtime.collect_events()

    assert len(events) == 1
    assert events[0].event_type == "test.event"
    assert events[0].source == "test_adapter"


def test_runtime_publish_requires_running():
    runtime = YomaEmbeddedRuntime()

    event = OperationalEvent(
        event_id="EV1",
        event_type="test.event",
        occurred_at=datetime.now(timezone.utc),
    )

    with pytest.raises(RuntimeError):
        runtime.publish(event)


def test_runtime_collect_requires_running():
    runtime = YomaEmbeddedRuntime()

    with pytest.raises(RuntimeError):
        runtime.collect_events()


def test_runtime_register_and_unregister_adapter():
    runtime = YomaEmbeddedRuntime()

    adapter = TestAdapter()

    runtime.register_adapter(adapter)

    assert runtime.status().adapter_count == 1

    assert runtime.unregister_adapter("test_adapter") is True
    assert runtime.status().adapter_count == 0


def test_runtime_can_publish_event():
    runtime = YomaEmbeddedRuntime()
    received = []

    runtime.bus.subscribe(received.append)

    runtime.start()

    event = OperationalEvent(
        event_id="EV2",
        event_type="manual.test",
        occurred_at=datetime.now(timezone.utc),
    )

    result = runtime.publish(event)

    assert result is event
    assert received == [event]
