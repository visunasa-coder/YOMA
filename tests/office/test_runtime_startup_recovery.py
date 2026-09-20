import pytest

from yoma.office.runtime import YomaEmbeddedRuntime


class FailingRestoreRuntime(YomaEmbeddedRuntime):
    def restore_integrations(self):
        raise RuntimeError("integration restore failed")


def test_failed_start_does_not_mark_runtime_running():
    runtime = FailingRestoreRuntime()

    with pytest.raises(RuntimeError, match="integration restore failed"):
        runtime.start()

    assert runtime.running is False
    assert runtime.status().scheduler_running is False


def test_failed_start_does_not_start_scheduler():
    runtime = FailingRestoreRuntime(
        collection_interval=3600,
    )

    with pytest.raises(RuntimeError):
        runtime.start()

    assert runtime.status().scheduler_running is False


def test_failed_start_can_be_retried():
    class RetryRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.attempts = 0

        def restore_integrations(self):
            self.attempts += 1

            if self.attempts == 1:
                raise RuntimeError("temporary failure")

            return []

    runtime = RetryRuntime()

    with pytest.raises(RuntimeError):
        runtime.start()

    assert runtime.running is False

    runtime.start()

    assert runtime.running is True
    assert runtime.attempts == 2

    runtime.stop()


def test_failed_start_does_not_corrupt_runtime_components():
    runtime = FailingRestoreRuntime()

    original_bus = runtime.bus
    original_scheduler = runtime.scheduler
    original_adapters = runtime.adapters

    with pytest.raises(RuntimeError):
        runtime.start()

    assert runtime.bus is original_bus
    assert runtime.scheduler is original_scheduler
    assert runtime.adapters is original_adapters


def test_failed_start_followed_by_stop_is_safe():
    runtime = FailingRestoreRuntime()

    with pytest.raises(RuntimeError):
        runtime.start()

    runtime.stop()

    assert runtime.running is False
    assert runtime.status().scheduler_running is False


def test_startup_failure_does_not_allow_runtime_operations():
    runtime = FailingRestoreRuntime()

    with pytest.raises(RuntimeError):
        runtime.start()

    with pytest.raises(RuntimeError):
        runtime.collect_events()

    with pytest.raises(RuntimeError):
        runtime.analyze([])

    with pytest.raises(RuntimeError):
        runtime.decide([])


def test_successful_retry_after_failure_starts_normally():
    class RecoveringRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.failed_once = False

        def restore_integrations(self):
            if not self.failed_once:
                self.failed_once = True
                raise RuntimeError("startup failure")

            return []

    runtime = RecoveringRuntime()

    with pytest.raises(RuntimeError):
        runtime.start()

    assert runtime.running is False

    runtime.start()

    status = runtime.status()

    assert status.running is True
    assert status.scheduler_running is True

    runtime.stop()
