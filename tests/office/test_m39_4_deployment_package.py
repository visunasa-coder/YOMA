import hashlib
import json

import pytest

from yoma.office.deployment_package import (
    DeploymentComponent,
    DeploymentPackage,
)


def make_package():
    return DeploymentPackage(
        package_id="yoma-enterprise",
        version="0.1.0",
        minimum_python_version="3.12",
        components=(
            DeploymentComponent(
                name="yoma-runtime",
                version="0.1.0",
                component_type="runtime",
            ),
            DeploymentComponent(
                name="yoma-control-server",
                version="0.1.0",
                component_type="windows-service",
            ),
        ),
    )


def test_component_is_immutable():
    component = DeploymentComponent(
        name="runtime",
        version="1.0.0",
        component_type="runtime",
    )

    with pytest.raises(AttributeError):
        component.name = "other"


def test_component_serialization():
    component = DeploymentComponent(
        name="runtime",
        version="1.0.0",
        component_type="runtime",
        required=False,
    )

    assert component.as_dict() == {
        "name": "runtime",
        "version": "1.0.0",
        "component_type": "runtime",
        "required": False,
    }


def test_component_rejects_empty_name():
    with pytest.raises(ValueError):
        DeploymentComponent(
            name="",
            version="1.0.0",
            component_type="runtime",
        )


def test_component_rejects_empty_version():
    with pytest.raises(ValueError):
        DeploymentComponent(
            name="runtime",
            version="",
            component_type="runtime",
        )


def test_component_rejects_empty_type():
    with pytest.raises(ValueError):
        DeploymentComponent(
            name="runtime",
            version="1.0.0",
            component_type="",
        )


def test_package_is_immutable():
    package = make_package()

    with pytest.raises(AttributeError):
        package.version = "2.0.0"


def test_package_manifest_contains_identity():
    manifest = make_package().manifest()

    assert manifest["manifest_version"] == "1"
    assert manifest["package_id"] == "yoma-enterprise"
    assert manifest["version"] == "0.1.0"
    assert manifest["minimum_python_version"] == "3.12"


def test_package_manifest_contains_components():
    components = make_package().manifest()["components"]

    assert len(components) == 2
    assert components[0]["name"] == "yoma-runtime"
    assert components[1]["component_type"] == "windows-service"


def test_package_requires_components():
    with pytest.raises(ValueError):
        DeploymentPackage(
            package_id="empty",
            version="0.1.0",
            minimum_python_version="3.12",
            components=(),
        )


@pytest.mark.parametrize(
    "field",
    [
        "package_id",
        "version",
        "minimum_python_version",
        "manifest_version",
    ],
)
def test_package_rejects_empty_metadata(field):
    values = {
        "package_id": "yoma",
        "version": "0.1.0",
        "minimum_python_version": "3.12",
        "components": (
            DeploymentComponent(
                name="runtime",
                version="0.1.0",
                component_type="runtime",
            ),
        ),
        "manifest_version": "1",
    }
    values[field] = ""

    with pytest.raises(ValueError):
        DeploymentPackage(**values)


def test_manifest_bytes_are_deterministic():
    package = make_package()

    assert package.manifest_bytes() == package.manifest_bytes()


def test_manifest_is_valid_json():
    package = make_package()

    parsed = json.loads(package.manifest_bytes())

    assert parsed == package.manifest()


def test_integrity_digest_is_sha256():
    package = make_package()

    expected = hashlib.sha256(package.manifest_bytes()).hexdigest()

    assert package.integrity_sha256() == expected


def test_integrity_digest_is_deterministic():
    package = make_package()

    assert package.integrity_sha256() == package.integrity_sha256()


def test_manifest_contains_no_secret_material():
    manifest = make_package().manifest()

    serialized = json.dumps(manifest).lower()

    assert "password" not in serialized
    assert "secret" not in serialized
    assert "api_key" not in serialized
    assert "credential_vault_key" not in serialized


def test_package_contains_no_execution_authority():
    package = make_package()

    assert not hasattr(package, "execute")
    assert not hasattr(package, "install")
    assert not hasattr(package, "authorize")


def test_component_required_defaults_true():
    component = DeploymentComponent(
        name="runtime",
        version="0.1.0",
        component_type="runtime",
    )

    assert component.required is True
