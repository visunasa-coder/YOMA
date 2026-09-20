from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost
from yoma.office.local_ipc import LocalIPCServer


def make_server():
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)

    return LocalIPCServer(
        host,
        secret="super-secret",
    )


def test_ipc_diagnostics_command():
    server = make_server()
    server.start()

    try:
        response = server.request(
            "diagnostics",
            secret="super-secret",
        )

        assert response["service"] == "yoma"
        assert response["service_state"] == "stopped"
        assert response["runtime_state"] == "stopped"
        assert response["runtime_running"] is False
        assert response["ipc_running"] is True
    finally:
        server.stop()


def test_diagnostics_requires_authentication():
    server = make_server()
    server.start()

    try:
        import pytest

        with pytest.raises(PermissionError):
            server.request("diagnostics")
    finally:
        server.stop()


def test_diagnostics_does_not_expose_secret():
    server = make_server()
    server.start()

    try:
        response = server.request(
            "diagnostics",
            secret="super-secret",
        )

        assert "secret" not in response
        assert "super-secret" not in str(response)
    finally:
        server.stop()


def test_diagnostics_reports_ipc_state():
    server = make_server()

    assert server.running is False

    server.start()

    try:
        response = server.request(
            "diagnostics",
            secret="super-secret",
        )

        assert response["ipc_running"] is True
    finally:
        server.stop()


def test_diagnostics_reports_runtime_state_after_runtime_start():
    server = make_server()

    server.host.start()
    server.start()

    try:
        response = server.request(
            "diagnostics",
            secret="super-secret",
        )

        assert response["service_state"] == "running"
        assert response["runtime_state"] == "running"
        assert response["runtime_running"] is True
        assert response["ipc_running"] is True
    finally:
        server.stop()
        server.host.stop()
