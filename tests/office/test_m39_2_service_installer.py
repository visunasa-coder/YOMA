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


def test_install_creates_installed_state(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()

    assert installer.installed() is True


def test_install_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.install()

    assert installer.installed() is True


def test_upgrade_requires_existing_installation(tmp_path):
    installer = make_installer(tmp_path)

    try:
        installer.upgrade(version="2.0.0")
    except RuntimeError as exc:
        assert str(exc) == "cannot upgrade an uninstalled service"
    else:
        raise AssertionError("upgrade should reject an uninstalled service")


def test_upgrade_preserves_existing_configuration(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.set_auto_start(True)

    installer.upgrade(version="2.0.0")

    state = installer._read_state()

    assert state["installed"] is True
    assert state["auto_start"] is True
    assert state["version"] == "2.0.0"
    assert state["lifecycle"] == "upgraded"


def test_upgrade_without_version_preserves_previous_version(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.upgrade(version="1.5.0")
    installer.upgrade()

    state = installer._read_state()

    assert state["version"] == "1.5.0"
    assert state["installed"] is True
    assert state["lifecycle"] == "upgraded"


def test_upgrade_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.upgrade(version="2.0.0")
    installer.upgrade(version="2.0.0")

    state = installer._read_state()

    assert state["version"] == "2.0.0"
    assert state["installed"] is True


def test_upgrade_rejects_empty_version(tmp_path):
    installer = make_installer(tmp_path)
    installer.install()

    try:
        installer.upgrade(version="")
    except ValueError as exc:
        assert str(exc) == "version must not be empty"
    else:
        raise AssertionError("empty version should be rejected")


def test_repair_creates_installation_state(tmp_path):
    installer = make_installer(tmp_path)

    installer.repair()

    assert installer.installed() is True
    assert installer._read_state()["lifecycle"] == "repaired"


def test_repair_preserves_configuration(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.set_auto_start(True)
    installer.upgrade(version="2.0.0")

    installer.repair()

    state = installer._read_state()

    assert state["installed"] is True
    assert state["auto_start"] is True
    assert state["version"] == "2.0.0"
    assert state["lifecycle"] == "repaired"


def test_repair_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.repair()
    installer.repair()

    assert installer.installed() is True


def test_uninstall_removes_installation_state(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.uninstall()

    assert installer.installed() is False


def test_uninstall_is_idempotent(tmp_path):
    installer = make_installer(tmp_path)

    installer.uninstall()
    installer.uninstall()

    assert installer.installed() is False


def test_uninstall_preserves_adapter(tmp_path):
    installer = make_installer(tmp_path)
    adapter = installer.adapter

    installer.install()
    installer.uninstall()

    assert installer.adapter is adapter


def test_lifecycle_operations_do_not_start_service(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    assert installer.status()["service_state"] == "stopped"

    installer.upgrade(version="2.0.0")
    assert installer.status()["service_state"] == "stopped"

    installer.repair()
    assert installer.status()["service_state"] == "stopped"


def test_install_defaults_auto_start_to_false(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()

    assert installer.auto_start() is False


def test_auto_start_survives_upgrade(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.set_auto_start(True)
    installer.upgrade(version="3.0.0")

    assert installer.auto_start() is True


def test_status_remains_available_after_repair(tmp_path):
    installer = make_installer(tmp_path)

    installer.repair()

    status = installer.status()

    assert status["installed"] is True
    assert status["service_state"] == "stopped"


def test_repair_recovers_from_corrupt_state(tmp_path):
    installer = make_installer(tmp_path)

    installer.state_path.parent.mkdir(parents=True, exist_ok=True)
    installer.state_path.write_text("{invalid json")

    installer.repair()

    assert installer.installed() is True
    assert installer.auto_start() is False


def test_upgrade_does_not_change_service_runtime(tmp_path):
    installer = make_installer(tmp_path)

    installer.install()
    installer.upgrade(version="4.0.0")

    assert installer.adapter.status()["state"] == "stopped"
    assert installer.adapter.status()["runtime_state"] == "stopped"
