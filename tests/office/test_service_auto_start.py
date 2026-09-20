from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost
from yoma.office.windows_service import WindowsServiceAdapter
from yoma.office.service_installer import ServiceInstaller


def make_installer(tmp_path):
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    return ServiceInstaller(
        adapter,
        state_path=tmp_path / "service-state.json",
    )


def test_auto_start_is_disabled_by_default(tmp_path):
    installer = make_installer(tmp_path)

    assert installer.auto_start() is False


def test_auto_start_can_be_enabled(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)

    assert installer.auto_start() is True


def test_auto_start_can_be_disabled(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)
    installer.set_auto_start(False)

    assert installer.auto_start() is False


def test_auto_start_configuration_persists(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)

    second = make_installer(tmp_path)

    assert second.auto_start() is True


def test_auto_start_disable_persists(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)
    installer.set_auto_start(False)

    second = make_installer(tmp_path)

    assert second.auto_start() is False


def test_auto_start_does_not_start_service(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)

    assert installer.adapter.host.running is False
    assert installer.status()["service_state"] == "stopped"


def test_auto_start_configuration_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)
    installer.set_auto_start(True)
    installer.set_auto_start(False)
    installer.set_auto_start(False)

    assert installer.auto_start() is False


def test_status_exposes_auto_start(tmp_path):
    installer = make_installer(tmp_path)

    installer.set_auto_start(True)

    status = installer.status()

    assert status["auto_start"] is True
