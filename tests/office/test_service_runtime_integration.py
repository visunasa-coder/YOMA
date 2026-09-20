from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost


def test_service_controls_embedded_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()

    assert runtime.running is True
    assert host.running is True

    host.stop()

    assert runtime.running is False


def test_service_uses_same_runtime_instance():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    assert host.runtime is runtime

    host.start()
    assert host.runtime is runtime
    host.stop()


def test_runtime_start_failure_is_exposed_by_service():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            self._runtime_state = "failed"
            raise RuntimeError("runtime failure")

    runtime = FailingRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.running is False
    assert host.status()["state"] == "failed"
    assert host.status()["runtime_state"] == "failed"


def test_service_stop_reaches_runtime():
    class TrackingRuntime(YomaEmbeddedRuntime):
        def __init__(self):
            super().__init__(collection_interval=3600)
            self.stop_called = False

        def stop(self):
            self.stop_called = True
            super().stop()

    runtime = TrackingRuntime()
    host = ServiceHost(runtime)

    host.start()
    host.stop()

    assert runtime.stop_called is True


def test_service_restart_reuses_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    original_runtime = host.runtime

    host.start()
    host.stop()
    host.start()

    assert host.runtime is original_runtime
    assert host.running is True

    host.stop()


def test_service_status_reflects_runtime_health():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    status = host.status()

    assert status["state"] == "stopped"
    assert status["runtime_state"] == "stopped"
    assert status["runtime_running"] is False


def test_service_does_not_replace_runtime_on_failure():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            raise RuntimeError("failure")

    runtime = FailingRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.runtime is runtime
    assert host.running is False


def test_service_lifecycle_remains_deterministic():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    assert host.status()["state"] == "running"

    host.stop()
    assert host.status()["state"] == "stopped"

    host.start()
    assert host.status()["state"] == "running"

    host.stop()
    assert host.status()["state"] == "stopped"
