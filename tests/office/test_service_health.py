from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost


def test_health_reports_stopped_service():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    health = host.health()

    assert health["healthy"] is False
    assert health["service_state"] == "stopped"
    assert health["runtime_state"] == "stopped"


def test_health_reports_running_service():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()

    health = host.health()

    assert health["healthy"] is True
    assert health["service_state"] == "running"
    assert health["runtime_state"] == "running"
    assert health["runtime_running"] is True

    host.stop()


def test_health_contains_service_identity():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    health = host.health()

    assert health["service"] == "yoma"


def test_health_contains_runtime_status():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    health = host.health()

    assert "runtime_running" in health
    assert "runtime_state" in health


def test_health_reflects_failed_service():
    class FailingRuntime(YomaEmbeddedRuntime):
        def start(self):
            self._runtime_state = "failed"
            raise RuntimeError("runtime startup failure")

    host = ServiceHost(FailingRuntime(collection_interval=3600))

    try:
        host.start()
    except RuntimeError:
        pass

    health = host.health()

    assert health["healthy"] is False
    assert health["service_state"] == "failed"
    assert health["runtime_state"] == "failed"


def test_health_is_safe_before_start():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    health = host.health()

    assert isinstance(health, dict)
    assert "healthy" in health
    assert "service_state" in health


def test_health_updates_after_restart():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    host.start()
    assert host.health()["healthy"] is True

    host.stop()
    assert host.health()["healthy"] is False

    host.start()
    assert host.health()["healthy"] is True

    host.stop()


def test_health_does_not_mutate_service_state():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    before = host.status()
    host.health()
    after = host.status()

    assert after["state"] == before["state"]
    assert after["runtime_state"] == before["runtime_state"]
