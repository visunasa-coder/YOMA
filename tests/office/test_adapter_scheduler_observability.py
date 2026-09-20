import time

from yoma.office.adapters import (
    AdapterCollectionScheduler,
    AdapterRuntimeManager,
    YomaAdapter,
)
from yoma.office.operations import OperationalEvent


class ObservableAdapter(YomaAdapter):
    category = "test"

    def __init__(self, name, failures=0):
        super().__init__()
        self.name = name
        self.failures = failures
        self.attempts = 0

    def health(self):
        return {
            "status": "healthy",
            "connected": self.connected,
        }

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        self.configure(config)
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        self.attempts += 1

        if self.attempts <= self.failures:
            raise RuntimeError("temporary failure")

        return [
            OperationalEvent(
                event_id=f"{self.name}-{self.attempts}",
                event_type="observable.test",
                occurred_at=time.time(),
                source=self.name,
            )
        ]


def test_adapter_status_created_after_collection():
    adapter = ObservableAdapter("observable_one")

    manager = AdapterRuntimeManager(max_retries=0)
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(manager)
    scheduler.run_once()

    status = scheduler.adapter_status("observable_one")

    assert status is not None
    assert status.adapter == "observable_one"
    assert status.status == "collected"
    assert status.collection_count == 1
    assert status.success_count == 1
    assert status.failure_count == 0
    assert status.events_collected == 1
    assert status.last_collection_at is not None
    assert status.last_error is None


def test_adapter_statistics_accumulate():
    adapter = ObservableAdapter("observable_two")

    manager = AdapterRuntimeManager(max_retries=0)
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(manager)

    scheduler.run_once()
    scheduler.run_once()
    scheduler.run_once()

    status = scheduler.adapter_status("observable_two")

    assert status is not None
    assert status.collection_count == 3
    assert status.success_count == 3
    assert status.failure_count == 0
    assert status.events_collected == 3


def test_adapter_failure_is_visible():
    adapter = ObservableAdapter(
        "observable_failure",
        failures=1,
    )

    manager = AdapterRuntimeManager(max_retries=0)
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(manager)

    scheduler.run_once()

    status = scheduler.adapter_status("observable_failure")

    assert status is not None
    assert status.status == "failed"
    assert status.collection_count == 1
    assert status.success_count == 0
    assert status.failure_count == 1
    assert status.events_collected == 0
    assert status.last_error == "RuntimeError"


def test_adapter_recovery_updates_statistics():
    adapter = ObservableAdapter(
        "observable_recovery",
        failures=1,
    )

    manager = AdapterRuntimeManager(max_retries=0)
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(manager)

    scheduler.run_once()
    scheduler.run_once()

    status = scheduler.adapter_status("observable_recovery")

    assert status is not None
    assert status.collection_count == 2
    assert status.success_count == 1
    assert status.failure_count == 1
    assert status.events_collected == 1
    assert status.status == "collected"
    assert status.last_error is None


def test_multiple_adapters_have_independent_statistics():
    first = ObservableAdapter("observable_first")
    second = ObservableAdapter(
        "observable_second",
        failures=1,
    )

    manager = AdapterRuntimeManager(max_retries=0)
    manager.register(first)
    manager.register(second)

    scheduler = AdapterCollectionScheduler(manager)
    scheduler.run_once()
    scheduler.run_once()

    first_status = scheduler.adapter_status("observable_first")
    second_status = scheduler.adapter_status("observable_second")

    assert first_status is not None
    assert second_status is not None

    assert first_status.success_count == 2
    assert first_status.failure_count == 0

    assert second_status.success_count == 1
    assert second_status.failure_count == 1


def test_scheduler_status_contains_adapter_statistics():
    adapter = ObservableAdapter("observable_status")

    manager = AdapterRuntimeManager(max_retries=0)
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(manager)
    scheduler.run_once()

    status = scheduler.status()

    assert len(status.adapters) == 1
    assert status.adapters[0].adapter == "observable_status"
    assert status.adapters[0].events_collected == 1
