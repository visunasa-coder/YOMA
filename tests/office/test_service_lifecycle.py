from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost


def test_service_lifecycle_starts_running():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()

    assert host.running is True
    assert host.status()["state"] == "running"

    host.stop()


def test_service_lifecycle_stops_cleanly():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.stop()

    assert host.running is False
    assert host.status()["state"] == "stopped"


def test_service_restart_after_clean_stop():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.stop()
    host.start()

    assert host.running is True
    assert host.status()["state"] == "running"

    host.stop()


def test_service_start_failure_sets_failed_state():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            raise RuntimeError("startup failure")

    host = ServiceHost(FailingRuntime(collection_interval=3600))

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.running is False
    assert host.status()["state"] == "failed"


def test_service_can_retry_after_failed_start():
    class RetryRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.attempts = 0

        def start(self):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("temporary failure")
            super().start()

    runtime = RetryRuntime()
    host = ServiceHost(runtime)

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.status()["state"] == "failed"

    host.start()

    assert host.running is True
    assert host.status()["state"] == "running"

    host.stop()


def test_service_stop_after_failed_start_is_safe():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            raise RuntimeError("startup failure")

    host = ServiceHost(FailingRuntime(collection_interval=3600))

    try:
        host.start()
    except RuntimeError:
        pass

    host.stop()

    assert host.running is False
    assert host.status()["state"] == "stopped"


def test_service_state_tracks_runtime_state():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()

    status = host.status()

    assert status["state"] == "running"
    assert status["runtime_state"] == "running"
    assert status["runtime_running"] is True

    host.stop()


def test_service_start_does_not_replace_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    original = host.runtime

    host.start()

    assert host.runtime is original

    host.stop()
