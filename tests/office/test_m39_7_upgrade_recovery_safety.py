from yoma.office.upgrade_recovery_safety import UpgradeRecoverySafety


def test_uninstalled_deployment_is_not_upgradeable():
    r = UpgradeRecoverySafety().assess(
        installed=False,
        lifecycle="",
        service_state="stopped",
        runtime_state="stopped",
    )
    assert r.safe is True
    assert r.upgrade_allowed is False
    assert r.repair_allowed is True


def test_running_deployment_can_be_upgraded():
    r = UpgradeRecoverySafety().assess(
        installed=True,
        lifecycle="installed",
        service_state="running",
        runtime_state="running",
    )
    assert r.safe is True
    assert r.upgrade_allowed is True


def test_failed_runtime_requires_recovery():
    r = UpgradeRecoverySafety().assess(
        installed=True,
        lifecycle="installed",
        service_state="failed",
        runtime_state="failed",
    )
    assert r.safe is False
    assert r.recovery_required is True
    assert r.upgrade_allowed is False


def test_startup_recovery_blocks_upgrade():
    r = UpgradeRecoverySafety().assess(
        installed=True,
        lifecycle="installed",
        service_state="stopped",
        runtime_state="stopped",
        startup_diagnostics={"recovery_required": True},
    )
    assert r.safe is False
    assert r.upgrade_allowed is False


def test_stopped_installation_is_upgradeable():
    r = UpgradeRecoverySafety().assess(
        installed=True,
        lifecycle="installed",
        service_state="stopped",
        runtime_state="stopped",
    )
    assert r.safe is True
    assert r.upgrade_allowed is True


def test_result_is_governed():
    r = UpgradeRecoverySafety().assess(
        installed=True,
        lifecycle="installed",
        service_state="running",
        runtime_state="running",
    )
    assert r.requires_human_approval is True
    assert r.executable is False


def test_result_serializes():
    r = UpgradeRecoverySafety().assess(
        installed=True,
        lifecycle="upgraded",
        service_state="running",
        runtime_state="running",
    )
    data = r.as_dict()
    assert data["lifecycle"] == "upgraded"
    assert data["upgrade_allowed"] is True
