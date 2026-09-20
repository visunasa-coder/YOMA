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


def test_ipc_server_starts_stopped():
    server = make_server()

    assert server.running is False


def test_ipc_server_can_start():
    server = make_server()

    server.start()

    assert server.running is True

    server.stop()


def test_ipc_server_can_stop():
    server = make_server()

    server.start()
    server.stop()

    assert server.running is False


def test_ipc_health_requires_authentication():
    server = make_server()
    server.start()

    try:
        with pytest.raises(PermissionError):
            server.request("health")
    finally:
        server.stop()


def test_ipc_health_accepts_valid_authentication():
    server = make_server()
    server.start()

    try:
        response = server.request(
            "health",
            secret="test-secret",
        )

        assert response["service"] == "yoma"
    finally:
        server.stop()


def test_ipc_rejects_invalid_authentication():
    server = make_server()
    server.start()

    try:
        with pytest.raises(PermissionError):
            server.request(
                "health",
                secret="wrong-secret",
            )
    finally:
        server.stop()


def test_ipc_can_return_runtime_status():
    server = make_server()
    server.start()

    try:
        response = server.request(
            "status",
            secret="test-secret",
        )

        assert response["state"] == "stopped"
        assert response["runtime_state"] == "stopped"
    finally:
        server.stop()


def test_ipc_does_not_expose_arbitrary_runtime_methods():
    server = make_server()
    server.start()

    try:
        with pytest.raises(ValueError):
            server.request(
                "runtime.start",
                secret="test-secret",
            )
    finally:
        server.stop()
