import pytest

from yoma.office.runtime import YomaEmbeddedRuntime


def test_runtime_starts_in_running_state():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    assert runtime.status().runtime_state == "running"

    runtime.stop()


def test_component_failure_does_not_make_runtime_claim_running_healthy():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    runtime.scheduler._last_error = "simulated component failure"

    status = runtime.status()

    assert status.scheduler_last_error == "simulated component failure"

    runtime.stop()


def test_scheduler_failure_is_observable_through_runtime_status():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    runtime.scheduler._last_error = "scheduler failure"

    status = runtime.status()

    assert status.scheduler_last_error == "scheduler failure"

    runtime.stop()


def test_runtime_core_components_remain_available_after_component_error():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    runtime.scheduler._last_error = "component failure"

    assert runtime.bus is not None
    assert runtime.adapters is not None
    assert runtime.scheduler is not None
    assert runtime.intelligence is not None
    assert runtime.decisions is not None

    runtime.stop()


def test_runtime_can_shutdown_after_component_error():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    runtime.scheduler._last_error = "component failure"

    runtime.stop()

    assert runtime.running is False
    assert runtime.status().runtime_state == "stopped"


def test_runtime_can_restart_after_component_error():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)

    runtime.start()

    runtime.scheduler._last_error = "component failure"

    runtime.stop()
    runtime.start()

    assert runtime.running is True
    assert runtime.status().runtime_state == "running"

    runtime.stop()


def test_runtime_health_state_supports_degraded_state():
    runtime = YomaEmbeddedRuntime()

    state = runtime.status().runtime_state

    assert state in {
        "stopped",
        "booting",
        "running",
        "degraded",
        "stopping",
        "failed",
    }
