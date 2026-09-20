from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.runtime import YomaEmbeddedRuntime


def test_control_runtime_owns_embedded_runtime():
    runtime = ControlServerRuntime(
        embedded_runtime=YomaEmbeddedRuntime()
    )

    assert runtime.embedded_runtime.running is False


def test_control_runtime_start_starts_embedded_runtime():
    runtime = ControlServerRuntime(
        host="127.0.0.1",
        port=18767,
    )

    try:
        runtime.start()

        assert runtime.running is True
        assert runtime.agent.running is True
        assert runtime.embedded_runtime.running is True
    finally:
        runtime.stop()


def test_control_runtime_stop_stops_embedded_runtime():
    runtime = ControlServerRuntime(
        host="127.0.0.1",
        port=18768,
    )

    runtime.start()

    assert runtime.embedded_runtime.running is True

    runtime.stop()

    assert runtime.embedded_runtime.running is False


def test_control_runtime_status_contains_embedded_runtime():
    runtime = ControlServerRuntime(
        embedded_runtime=YomaEmbeddedRuntime()
    )

    status = runtime.status()

    assert "embedded_runtime" in status
    assert status["embedded_runtime"]["running"] is False
    assert status["embedded_runtime"]["adapter_count"] == 0
    assert status["embedded_runtime"]["identity_provider"] is None


def test_control_runtime_start_is_idempotent():
    runtime = ControlServerRuntime(
        host="127.0.0.1",
        port=18769,
    )

    try:
        runtime.start()
        first_thread = runtime.thread

        runtime.start()

        assert runtime.thread is first_thread
        assert runtime.embedded_runtime.running is True
    finally:
        runtime.stop()


def test_control_runtime_stop_is_safe_when_not_started():
    runtime = ControlServerRuntime(
        embedded_runtime=YomaEmbeddedRuntime()
    )

    runtime.stop()

    assert runtime.running is False
    assert runtime.embedded_runtime.running is False
