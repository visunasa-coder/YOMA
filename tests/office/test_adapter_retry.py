from datetime import datetime, timezone

import pytest

from yoma.office.adapters import AdapterRuntimeManager, YomaAdapter
from yoma.office.operations import OperationalEvent


class FlakyAdapter(YomaAdapter):
    name = "flaky_runtime"
    category = "test"

    def __init__(self, failures_before_success=1):
        super().__init__()
        self.failures_remaining = failures_before_success
        self.connect_count = 0
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
        self.connect_count += 1

    def disconnect(self):
        self._connected = False

    def collect_events(self):
        self.collect_count += 1

        if self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise ConnectionError("temporary failure")

        return [
            OperationalEvent(
                event_id="RETRY-EVENT",
                event_type="test.event",
                occurred_at=datetime.now(timezone.utc),
                source=self.name,
            )
        ]


class AlwaysFailingAdapter(YomaAdapter):
    name = "always_failing"
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
        raise RuntimeError("permanent failure")


def test_retry_recovers_from_temporary_failure():
    adapter = FlakyAdapter(failures_before_success=1)

    manager = AdapterRuntimeManager(
        max_retries=2,
    )

    manager.register(adapter)

    manager.connect("flaky_runtime", {})

    events, result = manager.collect("flaky_runtime")

    assert result.status == "collected"
    assert result.events_collected == 1
    assert result.attempts == 2
    assert len(events) == 1
    assert adapter.connect_count >= 2


def test_retry_exhaustion_is_bounded():
    adapter = AlwaysFailingAdapter()

    manager = AdapterRuntimeManager(
        max_retries=2,
    )

    manager.register(adapter)

    manager.connect("always_failing", {})

    events, result = manager.collect("always_failing")

    assert events == []
    assert result.status == "failed"
    assert result.error == "RuntimeError"
    assert result.attempts == 3


def test_zero_retries_means_single_attempt():
    adapter = AlwaysFailingAdapter()

    manager = AdapterRuntimeManager(
        max_retries=0,
    )

    manager.register(adapter)

    manager.connect("always_failing", {})

    _, result = manager.collect("always_failing")

    assert result.status == "failed"
    assert result.attempts == 1


def test_negative_retry_count_rejected():
    with pytest.raises(ValueError):
        AdapterRuntimeManager(max_retries=-1)


def test_negative_retry_delay_rejected():
    with pytest.raises(ValueError):
        AdapterRuntimeManager(retry_delay=-1)


def test_retry_does_not_affect_other_adapters():
    good = FlakyAdapter(failures_before_success=1)
    good.name = "good_adapter"

    bad = AlwaysFailingAdapter()
    bad.name = "bad_adapter"

    manager = AdapterRuntimeManager(max_retries=1)

    manager.register(good)
    manager.register(bad)

    manager.connect("good_adapter", {})
    manager.connect("bad_adapter", {})

    events, results = manager.collect_all()

    result_map = {
        result.adapter: result
        for result in results
    }

    assert len(events) == 1
    assert result_map["good_adapter"].status == "collected"
    assert result_map["bad_adapter"].status == "failed"
