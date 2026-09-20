import pytest

from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost
from yoma.office.local_ipc import LocalIPCServer


def make_server():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    return LocalIPCServer(
        host,
        secret="test-secret",
    )


def test_ipc_request_requires_running_server():
    server = make_server()

    with pytest.raises(RuntimeError):
        server.request(
            "health",
            secret="test-secret",
        )


def test_ipc_request_works_after_start():
    server = make_server()

    server.start()

    response = server.request(
        "health",
        secret="test-secret",
    )

    assert response["service"] == "yoma"


def test_ipc_request_fails_after_stop():
    server = make_server()

    server.start()
    server.stop()

    with pytest.raises(RuntimeError):
        server.request(
            "health",
            secret="test-secret",
        )


def test_ipc_start_is_idempotent():
    server = make_server()

    server.start()
    server.start()

    assert server.running is True

    server.stop()


def test_ipc_stop_is_idempotent():
    server = make_server()

    server.start()
    server.stop()
    server.stop()

    assert server.running is False


def test_ipc_start_does_not_start_runtime():
    server = make_server()

    server.start()

    assert server.host.running is False

    server.stop()


def test_ipc_stop_does_not_stop_unrelated_runtime():
    server = make_server()

    server.host.start()
    server.start()

    server.stop()

    assert server.host.running is True

    server.host.stop()


def test_ipc_status_after_start_reports_service_state():
    server = make_server()

    server.start()

    response = server.request(
        "status",
        secret="test-secret",
    )

    assert response["state"] == "stopped"
    assert response["runtime_state"] == "stopped"

    server.stop()
