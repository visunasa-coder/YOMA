from pathlib import Path

from yoma.office.local_ipc import LocalIPCServer
from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost
from yoma.office.service_installer import ServiceInstaller
from yoma.office.windows_service import WindowsServiceAdapter


def make_system(tmp_path: Path):
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    installer = ServiceInstaller(
        adapter,
        state_path=tmp_path / "yoma-service.json",
    )

    ipc = LocalIPCServer(
        host,
        secret="integration-secret",
    )

    return runtime, host, adapter, installer, ipc


def test_complete_service_installation_and_ipc_flow(tmp_path):
    runtime, host, adapter, installer, ipc = make_system(tmp_path)

    assert installer.installed() is False

    installer.install()
    installer.set_auto_start(True)

    assert installer.installed() is True
    assert installer.auto_start() is True

    adapter.start()
    ipc.start()

    try:
        assert host.running is True
        assert ipc.running is True

        health = ipc.request(
            "health",
            secret="integration-secret",
        )

        assert health["service"] == "yoma"
        assert health["healthy"] is True

        diagnostics = ipc.request(
            "diagnostics",
            secret="integration-secret",
        )

        assert diagnostics["service_state"] == "running"
        assert diagnostics["runtime_state"] == "running"
        assert diagnostics["runtime_running"] is True
        assert diagnostics["ipc_running"] is True
    finally:
        ipc.stop()
        adapter.stop()


def test_service_restart_preserves_installation(tmp_path):
    runtime, host, adapter, installer, ipc = make_system(tmp_path)

    installer.install()
    installer.set_auto_start(True)

    adapter.start()
    ipc.start()

    ipc.stop()
    adapter.stop()

    assert installer.installed() is True
    assert installer.auto_start() is True

    adapter.start()
    ipc.start()

    try:
        response = ipc.request(
            "status",
            secret="integration-secret",
        )

        assert response["state"] == "running"
        assert response["runtime_state"] == "running"
    finally:
        ipc.stop()
        adapter.stop()


def test_uninstall_removes_persistent_installation_state(tmp_path):
    runtime, host, adapter, installer, ipc = make_system(tmp_path)

    installer.install()
    installer.set_auto_start(True)

    assert installer.installed() is True

    installer.uninstall()

    assert installer.installed() is False
    assert installer.auto_start() is False
