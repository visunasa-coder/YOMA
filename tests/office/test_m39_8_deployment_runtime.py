from yoma.office.deployment_runtime import EnterpriseDeploymentRuntime


def healthy_service():
    return {
        "healthy": True,
        "service_state": "running",
        "runtime_state": "running",
        "runtime_running": True,
    }


def test_ready_deployment():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.ready is True
    assert result.healthy is True


def test_uninstalled_deployment_not_ready():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=False,
        installation_state="",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.ready is False
    assert result.installed is False


def test_recovery_blocks_readiness():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
        recovery_required=True,
    )

    assert result.ready is False
    assert result.recovery_required is True
    assert result.upgrade_allowed is False


def test_bad_package_blocks_readiness():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=False,
        secret_boundary_valid=True,
    )

    assert result.ready is False
    assert result.package_integrity is False


def test_bad_secret_boundary_blocks_readiness():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=False,
    )

    assert result.ready is False
    assert result.secret_boundary_valid is False


def test_unhealthy_service_blocks_readiness():
    service = healthy_service()
    service["healthy"] = False

    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=service,
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.ready is False
    assert result.healthy is False


def test_upgrade_allowed_when_safe():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.upgrade_allowed is True


def test_upgrade_blocked_by_integrity():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=False,
        secret_boundary_valid=True,
    )

    assert result.upgrade_allowed is False


def test_upgrade_blocked_by_secret_boundary():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=False,
    )

    assert result.upgrade_allowed is False


def test_result_is_governed():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.requires_human_approval is True
    assert result.executable is False


def test_result_serializes():
    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    data = result.as_dict()

    assert data["deployment_id"] == "dep-1"
    assert data["organization_id"] == "org-1"
    assert data["ready"] is True


def test_running_flag_is_required():
    service = healthy_service()
    service["runtime_running"] = False

    result = EnterpriseDeploymentRuntime().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installed=True,
        installation_state="installed",
        service_health=service,
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.ready is False
