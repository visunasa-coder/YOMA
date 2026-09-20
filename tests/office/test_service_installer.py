from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost
from yoma.office.windows_service import WindowsServiceAdapter
from yoma.office.service_installer import ServiceInstaller


def make_installer(tmp_path):
    runtime = YomaEmbeddedRuntime(collection_interval=3600)
    host = ServiceHost(runtime)
    adapter = WindowsServiceAdapter(host)

    return ServiceInstaller(adapter, state_path=tmp_path / "service-state.json")


def test_service_installer_starts_uninstalled(tmp_path):
    installer = make_installer(tmp_path)

    assert installer.installed() is False


def test_install_marks_service_installed(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()

    assert installer.installed() is True


def test_install_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.install()

    assert installer.installed() is True


def test_uninstall_marks_service_uninstalled(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.uninstall()

    assert installer.installed() is False


def test_uninstall_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.uninstall()
    installer.uninstall()

    assert installer.installed() is False


def test_installer_exposes_service_status(tmp_path):
    installer = make_installer(tmp_path)

    status = installer.status()

    assert status["installed"] is False
    assert status["service_state"] == "stopped"


def test_install_does_not_start_service(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()

    status = installer.status()

    assert status["installed"] is True
    assert status["service_state"] == "stopped"


def test_uninstall_does_not_destroy_service_adapter(tmp_path):
    installer = make_installer(tmp_path)

    adapter = installer.adapter

    installer.install()
    installer.uninstall()

    assert installer.adapter is adapter
