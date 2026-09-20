import pytest

from yoma.office.deployment_secret_boundary import (
    DeploymentSecretBoundary,
    SecretReference,
)


def test_secret_reference_is_immutable():
    reference = SecretReference("google-oauth")

    with pytest.raises(AttributeError):
        reference.name = "other"


def test_secret_reference_defaults_to_credential_vault():
    reference = SecretReference("google-oauth")

    assert reference.provider == "credential_vault"


def test_secret_reference_serializes_reference_only():
    reference = SecretReference(
        "google-oauth",
        provider="credential_vault",
    )

    assert reference.as_dict() == {
        "name": "google-oauth",
        "provider": "credential_vault",
    }


def test_secret_reference_rejects_empty_name():
    with pytest.raises(ValueError):
        SecretReference("")


def test_secret_reference_rejects_empty_provider():
    with pytest.raises(ValueError):
        SecretReference("google-oauth", provider="")


def test_boundary_is_immutable():
    boundary = DeploymentSecretBoundary(
        secret_references=(SecretReference("google-oauth"),)
    )

    with pytest.raises(AttributeError):
        boundary.secret_references = ()


def test_boundary_returns_reference_names():
    boundary = DeploymentSecretBoundary(
        secret_references=(
            SecretReference("google-oauth"),
            SecretReference("ai-provider"),
        )
    )

    assert boundary.references() == (
        "google-oauth",
        "ai-provider",
    )


def test_boundary_serialization_contains_references_only():
    boundary = DeploymentSecretBoundary(
        secret_references=(SecretReference("google-oauth"),)
    )

    assert boundary.as_dict() == {
        "secret_references": [
            {
                "name": "google-oauth",
                "provider": "credential_vault",
            }
        ]
    }


@pytest.mark.parametrize(
    "field",
    [
        "password",
        "secret",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "token",
        "credential",
        "credential_value",
        "master_key",
        "private_key",
    ],
)
def test_boundary_detects_secret_fields(field):
    boundary = DeploymentSecretBoundary()

    assert boundary.contains_secret_fields(
        {
            "organization_id": "org-1",
            field: "DO-NOT-STORE",
        }
    ) is True


def test_boundary_accepts_normal_configuration():
    boundary = DeploymentSecretBoundary()

    assert boundary.contains_secret_fields(
        {
            "organization_id": "org-1",
            "environment": "production",
            "runtime_mode": "embedded",
        }
    ) is False


def test_boundary_rejects_secret_configuration():
    boundary = DeploymentSecretBoundary()

    with pytest.raises(ValueError):
        boundary.validate_configuration(
            {
                "organization_id": "org-1",
                "api_key": "secret-value",
            }
        )


def test_boundary_accepts_non_secret_configuration():
    boundary = DeploymentSecretBoundary()

    boundary.validate_configuration(
        {
            "organization_id": "org-1",
            "environment": "production",
            "runtime_mode": "embedded",
        }
    )


def test_sanitize_removes_secret_fields():
    boundary = DeploymentSecretBoundary()

    result = boundary.sanitize(
        {
            "organization_id": "org-1",
            "environment": "production",
            "api_key": "SUPER-SECRET",
            "password": "PASSWORD",
        }
    )

    assert result == {
        "organization_id": "org-1",
        "environment": "production",
    }


def test_sanitize_preserves_non_secret_values():
    boundary = DeploymentSecretBoundary()

    configuration = {
        "organization_id": "org-1",
        "environment": "production",
        "runtime_mode": "embedded",
        "port": 8765,
    }

    assert boundary.sanitize(configuration) == configuration


def test_sanitize_does_not_mutate_input():
    boundary = DeploymentSecretBoundary()

    configuration = {
        "organization_id": "org-1",
        "api_key": "secret",
    }

    boundary.sanitize(configuration)

    assert configuration["api_key"] == "secret"


def test_boundary_never_contains_secret_values():
    boundary = DeploymentSecretBoundary(
        secret_references=(
            SecretReference("google-oauth"),
        )
    )

    serialized = str(boundary.as_dict()).lower()

    assert "password" not in serialized
    assert "secret-value" not in serialized
    assert "api_key" not in serialized


def test_existing_credential_vault_remains_external_to_boundary():
    boundary = DeploymentSecretBoundary(
        secret_references=(
            SecretReference("google-oauth"),
        )
    )

    assert boundary.references() == ("google-oauth",)


def test_boundary_does_not_provide_secret_retrieval():
    boundary = DeploymentSecretBoundary()

    assert not hasattr(boundary, "retrieve")
    assert not hasattr(boundary, "get_secret")
    assert not hasattr(boundary, "store")


def test_boundary_does_not_grant_execution_authority():
    boundary = DeploymentSecretBoundary()

    assert not hasattr(boundary, "execute")
    assert not hasattr(boundary, "authorize")
    assert not hasattr(boundary, "approve")
