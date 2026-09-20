import pytest

from yoma.office.runtime import YomaEmbeddedRuntime


def test_initial_runtime_state_is_stopped():
    runtime = YomaEmbeddedRuntime()

    assert runtime.status().runtime_state == "stopped"


def test_runtime_state_becomes_running_after_start():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    assert runtime.status().runtime_state == "running"

    runtime.stop()


def test_runtime_state_returns_to_stopped_after_stop():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()
    runtime.stop()

    assert runtime.status().runtime_state == "stopped"


def test_runtime_state_remains_stopped_after_repeated_stop():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.stop()
    runtime.stop()

    assert runtime.status().runtime_state == "stopped"


def test_failed_start_does_not_report_running_state():
    class FailingRuntime(YomaEmbeddedRuntime):
        def restore_integrations(self):
            raise RuntimeError("startup failure")

    runtime = FailingRuntime()

    with pytest.raises(RuntimeError, match="startup failure"):
        runtime.start()

    assert runtime.status().runtime_state != "running"
    assert runtime.running is False


def test_runtime_health_state_is_consistent_with_running_flag():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    assert runtime.status().runtime_state == "stopped"
    assert runtime.running is False

    runtime.start()

    assert runtime.status().runtime_state == "running"
    assert runtime.running is True

    runtime.stop()

    assert runtime.status().runtime_state == "stopped"
    assert runtime.running is False


def test_runtime_state_is_exposed_as_string():
    runtime = YomaEmbeddedRuntime()

    state = runtime.status().runtime_state

    assert isinstance(state, str)
    assert state in {
        "stopped",
        "booting",
        "running",
        "degraded",
        "stopping",
        "failed",
    }
