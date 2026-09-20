import pytest

from yoma.office.deployment_health import (
    DeploymentHealth,
    DeploymentHealthResult,
)


def healthy_service():
    return {
        "service": "yoma",
        "healthy": True,
        "service_state": "running",
        "runtime_state": "running",
        "runtime_running": True,
    }


def test_result_is_immutable():
    result = DeploymentHealthResult(
        healthy=True,
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_state="running",
        runtime_state="running",
        package_integrity=True,
        secret_boundary_valid=True,
    )

    with pytest.raises(AttributeError):
        result.healthy = False


def test_healthy_deployment():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is True


def test_unhealthy_when_service_is_stopped():
    service = healthy_service()
    service["healthy"] = False
    service["service_state"] = "stopped"
    service["runtime_state"] = "stopped"
    service["runtime_running"] = False

    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=service,
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is False


def test_unhealthy_when_not_installed():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="uninstalled",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is False


def test_unhealthy_when_package_integrity_fails():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=False,
        secret_boundary_valid=True,
    )

    assert result.healthy is False


def test_unhealthy_when_secret_boundary_fails():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=False,
    )

    assert result.healthy is False


def test_upgraded_installation_is_healthy():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="upgraded",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is True


def test_repaired_installation_is_healthy():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="repaired",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is True


def test_diagnostics_are_preserved():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
        diagnostics=("startup clean", "package verified"),
    )

    assert result.diagnostics == ("startup clean", "package verified")


def test_diagnostics_are_safe():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
        diagnostics=("package verified",),
    )

    diagnostics = DeploymentHealth().diagnostics(result)

    assert "super-secret" not in str(diagnostics)
    assert "password123" not in str(diagnostics)


def test_diagnostics_serialization():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    data = result.as_dict()

    assert data["deployment_id"] == "dep-1"
    assert data["organization_id"] == "org-1"
    assert data["package_integrity"] is True
    assert data["secret_boundary_valid"] is True


def test_result_requires_human_approval():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.requires_human_approval is True


def test_result_is_not_executable():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.executable is False


def test_invalid_service_health_type():
    with pytest.raises(TypeError):
        DeploymentHealth().assess(
            deployment_id="dep-1",
            organization_id="org-1",
            installation_state="installed",
            service_health=None,
            package_integrity=True,
            secret_boundary_valid=True,
        )


def test_empty_deployment_id_rejected():
    with pytest.raises(ValueError):
        DeploymentHealth().assess(
            deployment_id="",
            organization_id="org-1",
            installation_state="installed",
            service_health=healthy_service(),
            package_integrity=True,
            secret_boundary_valid=True,
        )


def test_empty_organization_id_rejected():
    with pytest.raises(ValueError):
        DeploymentHealth().assess(
            deployment_id="dep-1",
            organization_id="",
            installation_state="installed",
            service_health=healthy_service(),
            package_integrity=True,
            secret_boundary_valid=True,
        )


def test_unknown_service_state_makes_deployment_unhealthy():
    service = healthy_service()
    service["service_state"] = "unknown"

    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=service,
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is False


def test_runtime_running_flag_must_be_true():
    service = healthy_service()
    service["runtime_running"] = False

    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=service,
        package_integrity=True,
        secret_boundary_valid=True,
    )

    assert result.healthy is False


def test_diagnostics_result_has_no_execution_authority():
    result = DeploymentHealth().assess(
        deployment_id="dep-1",
        organization_id="org-1",
        installation_state="installed",
        service_health=healthy_service(),
        package_integrity=True,
        secret_boundary_valid=True,
    )

    diagnostics = DeploymentHealth().diagnostics(result)

    assert diagnostics["requires_human_approval"] is True
    assert diagnostics["executable"] is False
