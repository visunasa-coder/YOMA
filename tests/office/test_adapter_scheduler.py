import time

import pytest

from yoma.office.adapters import (
    AdapterCollectionScheduler,
    AdapterRuntimeManager,
    YomaAdapter,
)
from yoma.office.operations import OperationalEvent


class SchedulerAdapter(YomaAdapter):
    name = "scheduler_test"
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
                event_id=f"scheduler-event-{self.collection_count}",
                event_type="test.event",
                occurred_at=time.time(),
                source=self.name,
                data={"cycle": self.collection_count},
            )
        ]


def test_run_once_collects_events():
    adapter = SchedulerAdapter()
    manager = AdapterRuntimeManager()
    manager.register(adapter)

    received = []

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=60,
        on_events=received.extend,
    )

    scheduler.run_once()

    status = scheduler.status()

    assert status.running is False
    assert status.cycle_count == 1
    assert status.events_collected == 1
    assert len(received) == 1
    assert adapter.collection_count == 1


def test_scheduler_starts_and_stops():
    adapter = SchedulerAdapter()
    manager = AdapterRuntimeManager()
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=0.02,
    )

    scheduler.start()

    time.sleep(0.08)

    assert scheduler.running is True
    assert scheduler.status().cycle_count >= 1

    scheduler.stop()

    assert scheduler.running is False


def test_start_is_idempotent():
    manager = AdapterRuntimeManager()

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=60,
    )

    scheduler.start()
    first_thread = scheduler._thread

    scheduler.start()

    assert scheduler._thread is first_thread

    scheduler.stop()


def test_stop_is_idempotent():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=60,
    )

    scheduler.stop()
    scheduler.stop()

    assert scheduler.running is False


def test_invalid_interval_rejected():
    manager = AdapterRuntimeManager()

    with pytest.raises(ValueError):
        AdapterCollectionScheduler(manager, interval=0)

    with pytest.raises(ValueError):
        AdapterCollectionScheduler(manager, interval=-1)


def test_collection_errors_are_recorded():
    class FailingManager:
        def collect_all(self):
            raise RuntimeError("collection failed")

    scheduler = AdapterCollectionScheduler(
        FailingManager(),
        interval=60,
    )

    scheduler.run_once()

    status = scheduler.status()

    assert status.cycle_count == 1
    assert status.last_error == "RuntimeError"
    assert status.running is False
