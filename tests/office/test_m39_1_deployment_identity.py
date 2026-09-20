from pathlib import Path

import pytest

from yoma.office.deployment_identity import (
    DeploymentConfiguration,
    DeploymentIdentity,
)


def make_identity(tmp_path):
    return DeploymentIdentity(
        deployment_id="dep-001",
        organization_id="org-001",
        edition="enterprise",
        version="1.0.0",
        environment="production",
        installation_path=tmp_path / "YOMA",
        configuration_path=tmp_path / "YOMA" / "config",
    )


def test_deployment_identity_is_immutable(tmp_path):
    identity = make_identity(tmp_path)

    with pytest.raises(AttributeError):
        identity.deployment_id = "other"


def test_deployment_identity_preserves_identity(tmp_path):
    identity = make_identity(tmp_path)

    assert identity.deployment_id == "dep-001"
    assert identity.organization_id == "org-001"
    assert identity.edition == "enterprise"
    assert identity.version == "1.0.0"
    assert identity.environment == "production"


def test_deployment_identity_paths_are_paths(tmp_path):
    identity = make_identity(tmp_path)

    assert isinstance(identity.installation_path, Path)
    assert isinstance(identity.configuration_path, Path)


def test_enterprise_detection(tmp_path):
    assert make_identity(tmp_path).is_enterprise is True


def test_non_enterprise_detection(tmp_path):
    identity = make_identity(tmp_path)

    other = DeploymentIdentity(
        deployment_id=identity.deployment_id,
        organization_id=identity.organization_id,
        edition="professional",
        version=identity.version,
        environment=identity.environment,
        installation_path=identity.installation_path,
        configuration_path=identity.configuration_path,
    )

    assert other.is_enterprise is False


def test_identity_serialization_is_deterministic(tmp_path):
    identity = make_identity(tmp_path)

    assert identity.as_dict() == {
        "deployment_id": "dep-001",
        "organization_id": "org-001",
        "edition": "enterprise",
        "version": "1.0.0",
        "environment": "production",
        "installation_path": str(tmp_path / "YOMA"),
        "configuration_path": str(tmp_path / "YOMA" / "config"),
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("deployment_id", ""),
        ("organization_id", ""),
        ("edition", ""),
        ("version", ""),
        ("environment", ""),
    ],
)
def test_identity_rejects_empty_required_fields(tmp_path, field, value):
    values = {
        "deployment_id": "dep-001",
        "organization_id": "org-001",
        "edition": "enterprise",
        "version": "1.0.0",
        "environment": "production",
        "installation_path": tmp_path / "YOMA",
        "configuration_path": tmp_path / "YOMA" / "config",
    }
    values[field] = value

    with pytest.raises(ValueError):
        DeploymentIdentity(**values)


def test_identity_rejects_non_path_installation(tmp_path):
    with pytest.raises(TypeError):
        DeploymentIdentity(
            deployment_id="dep-001",
            organization_id="org-001",
            edition="enterprise",
            version="1.0.0",
            environment="production",
            installation_path=str(tmp_path / "YOMA"),
            configuration_path=tmp_path / "config",
        )


def test_identity_rejects_non_path_configuration(tmp_path):
    with pytest.raises(TypeError):
        DeploymentIdentity(
            deployment_id="dep-001",
            organization_id="org-001",
            edition="enterprise",
            version="1.0.0",
            environment="production",
            installation_path=tmp_path / "YOMA",
            configuration_path=str(tmp_path / "config"),
        )


def test_configuration_defaults(tmp_path):
    configuration = DeploymentConfiguration(make_identity(tmp_path))

    assert configuration.service_name == "YOMA"
    assert configuration.auto_start is False


def test_configuration_serialization(tmp_path):
    configuration = DeploymentConfiguration(
        make_identity(tmp_path),
        service_name="YOMA Enterprise",
        auto_start=True,
    )

    result = configuration.as_dict()

    assert result["service_name"] == "YOMA Enterprise"
    assert result["auto_start"] is True
    assert result["organization_id"] == "org-001"


def test_configuration_rejects_empty_service_name(tmp_path):
    with pytest.raises(ValueError):
        DeploymentConfiguration(
            make_identity(tmp_path),
            service_name="",
        )


def test_configuration_contains_no_secret_fields(tmp_path):
    result = DeploymentConfiguration(make_identity(tmp_path)).as_dict()

    assert "password" not in result
    assert "secret" not in result
    assert "api_key" not in result
    assert "credential_vault_key" not in result
