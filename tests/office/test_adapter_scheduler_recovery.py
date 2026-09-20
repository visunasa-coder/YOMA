import time

from yoma.office.adapters import (
    AdapterCollectionScheduler,
    AdapterRuntimeManager,
    YomaAdapter,
)
from yoma.office.operations import OperationalEvent


class RecoveringAdapter(YomaAdapter):
    name = "recovering_adapter"
    category = "test"

    def __init__(self, failures_before_success: int = 1):
        super().__init__()
        self.failures_before_success = failures_before_success
        self.collection_count = 0
        self.attempt_count = 0

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
        self.attempt_count += 1

        if self.attempt_count <= self.failures_before_success:
            raise RuntimeError("temporary collection failure")

        self.collection_count += 1

        return [
            OperationalEvent(
                event_id=f"recovery-{self.collection_count}",
                event_type="recovery.test",
                occurred_at=time.time(),
                source=self.name,
            )
        ]


class AlwaysFailingAdapter(YomaAdapter):
    name = "always_failing_scheduler"
    category = "test"

    def __init__(self):
        super().__init__()
        self.collection_attempts = 0

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
        self.collection_attempts += 1
        raise RuntimeError("permanent failure")


class HealthyAdapter(YomaAdapter):
    name = "healthy_scheduler"
    category = "test"

    def __init__(self):
        super().__init__()
        self.collection_count = 0

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
        self.collection_count += 1

        return [
            OperationalEvent(
                event_id=f"healthy-{self.collection_count}",
                event_type="healthy.test",
                occurred_at=time.time(),
                source=self.name,
            )
        ]


def test_scheduler_survives_permanent_adapter_failure():
    adapter = AlwaysFailingAdapter()

    manager = AdapterRuntimeManager(
        max_retries=1,
    )
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=0.02,
    )

    scheduler.start()

    time.sleep(0.10)

    assert scheduler.running is True
    assert scheduler.status().cycle_count >= 2
    assert adapter.collection_attempts >= 2

    scheduler.stop()

    assert scheduler.running is False


def test_scheduler_recovers_after_temporary_failure():
    adapter = RecoveringAdapter(failures_before_success=1)

    manager = AdapterRuntimeManager(
        max_retries=1,
    )
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=0.02,
    )

    scheduler.start()

    time.sleep(0.08)

    scheduler.stop()

    status = scheduler.status()

    assert status.cycle_count >= 1
    assert status.events_collected >= 1
    assert adapter.collection_count >= 1
    assert adapter.attempt_count >= 2


def test_failed_adapter_does_not_stop_healthy_adapter():
    failing = AlwaysFailingAdapter()
    healthy = HealthyAdapter()

    manager = AdapterRuntimeManager(
        max_retries=1,
    )
    manager.register(failing)
    manager.register(healthy)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=0.02,
    )

    scheduler.start()

    time.sleep(0.08)

    scheduler.stop()

    assert failing.collection_attempts >= 1
    assert healthy.collection_count >= 1
    assert scheduler.status().events_collected >= 1
    assert (
    scheduler.status().last_error
    == "always_failing_scheduler:RuntimeError"
)


def test_scheduler_stop_recovers_cleanly_after_failure():
    adapter = AlwaysFailingAdapter()

    manager = AdapterRuntimeManager(
        max_retries=2,
    )
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=0.02,
    )

    scheduler.start()

    time.sleep(0.04)
    scheduler.stop()

    assert scheduler.running is False
    assert scheduler._thread is None


def test_scheduler_failure_does_not_raise_to_caller():
    adapter = AlwaysFailingAdapter()

    manager = AdapterRuntimeManager(
        max_retries=0,
    )
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=60,
    )

    scheduler.run_once()

    status = scheduler.status()

    assert status.cycle_count == 1
    assert status.events_collected == 0
    assert status.running is False
