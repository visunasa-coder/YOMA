from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost
from yoma.office.windows_service import WindowsServiceAdapter


def test_windows_service_adapter_wraps_service_host():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    assert adapter.host is host


def test_windows_service_adapter_starts_host():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    adapter.start()

    assert host.running is True
    assert runtime.running is True

    adapter.stop()


def test_windows_service_adapter_stops_host():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    adapter.start()
    adapter.stop()

    assert host.running is False
    assert runtime.running is False


def test_windows_service_adapter_start_is_idempotent():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    adapter.start()
    adapter.start()

    assert host.running is True

    adapter.stop()


def test_windows_service_adapter_stop_is_idempotent():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    adapter.stop()
    adapter.stop()

    assert host.running is False


def test_windows_service_adapter_exposes_status():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    status = adapter.status()

    assert status["state"] == "stopped"
    assert status["runtime_state"] == "stopped"


def test_windows_service_adapter_propagates_start_failure():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            raise RuntimeError("windows service startup failure")

    runtime = FailingRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    try:
        adapter.start()
    except RuntimeError:
        pass

    assert adapter.status()["state"] == "failed"


def test_windows_service_adapter_preserves_host_and_runtime():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    adapter.start()
    adapter.stop()

    assert adapter.host is host
    assert adapter.host.runtime is runtime
