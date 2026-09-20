from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost


def test_service_host_starts_stopped():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    assert host.running is False
    assert host.status()["state"] == "stopped"


def test_service_host_starts_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()

    assert host.running is True
    assert runtime.running is True
    assert host.status()["state"] == "running"

    host.stop()


def test_service_host_start_is_idempotent():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.start()

    assert host.running is True
    assert runtime.running is True

    host.stop()


def test_service_host_stops_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    host.stop()

    assert host.running is False
    assert runtime.running is False
    assert host.status()["state"] == "stopped"


def test_service_host_stop_is_idempotent():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.stop()
    host.stop()

    assert host.running is False
    assert runtime.running is False


def test_service_host_preserves_runtime_instance():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    assert host.runtime is runtime


def test_service_host_reports_runtime_health():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    status = host.status()

    assert status["state"] == "stopped"
    assert "runtime_state" in status
    assert "runtime_running" in status


def test_service_host_shutdown_after_runtime_failure():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            self._runtime_state = "failed"
            raise RuntimeError("service startup failure")

    runtime = FailingRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    try:
        host.start()
    except RuntimeError:
        pass

    assert host.running is False
    assert host.status()["state"] == "failed"

    host.stop()

    assert host.running is False
