import time

import pytest

from yoma.office.adapters import (
    AdapterCollectionScheduler,
    AdapterRuntimeManager,
    YomaAdapter,
)


class ControlAdapter(YomaAdapter):
    name = "scheduler_control"
    category = "test"

    def __init__(self):
        super().__init__()
        self.collection_count = 0

    def health(self):
        return {"status": "healthy", "connected": self.connected}

    def capabilities(self):
        return ["events"]

    def connect(self, config):
        self.configure(config)
        self._connected = True

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        self.collection_count += 1
        return []


def test_scheduler_can_be_disabled():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=0.02,
        enabled=False,
    )

    scheduler.start()

    assert scheduler.running is False
    assert scheduler.status().enabled is False


def test_enabling_scheduler_allows_start():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=0.02,
        enabled=False,
    )

    scheduler.start()
    assert scheduler.running is False

    scheduler.set_enabled(True)
    scheduler.start()

    assert scheduler.running is True

    scheduler.stop()


def test_disabling_running_scheduler_stops_it():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=0.02,
    )

    scheduler.start()
    assert scheduler.running is True

    scheduler.set_enabled(False)

    assert scheduler.running is False
    assert scheduler.status().enabled is False


def test_interval_can_be_changed():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=10.0,
    )

    scheduler.set_interval(5.0)

    assert scheduler.status().interval == 5.0


def test_invalid_interval_update_rejected():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=10.0,
    )

    with pytest.raises(ValueError):
        scheduler.set_interval(0)

    with pytest.raises(ValueError):
        scheduler.set_interval(-1)

    assert scheduler.status().interval == 10.0


def test_status_reports_enabled_and_interval():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=15.0,
        enabled=False,
    )

    status = scheduler.status()

    assert status.enabled is False
    assert status.interval == 15.0
    assert status.running is False


def test_disabled_scheduler_can_still_run_manual_collection():
    adapter = ControlAdapter()

    manager = AdapterRuntimeManager()
    manager.register(adapter)

    scheduler = AdapterCollectionScheduler(
        manager,
        interval=60.0,
        enabled=False,
    )

    scheduler.run_once()

    assert adapter.collection_count == 1
    assert scheduler.status().cycle_count == 1
    assert scheduler.running is False


def test_start_remains_idempotent_with_production_controls():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=0.02,
    )

    scheduler.start()
    first_thread = scheduler._thread

    scheduler.start()

    assert scheduler._thread is first_thread

    scheduler.stop()


def test_runtime_status_updates_after_interval_change():
    scheduler = AdapterCollectionScheduler(
        AdapterRuntimeManager(),
        interval=1.0,
    )

    scheduler.set_interval(0.5)

    assert scheduler.status().interval == 0.5

    time.sleep(0.01)
