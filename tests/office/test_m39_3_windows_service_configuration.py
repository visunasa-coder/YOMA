import pytest

from yoma.office.windows_service_configuration import (
    WindowsServiceConfiguration,
)


def test_default_service_configuration():
    config = WindowsServiceConfiguration()

    assert config.service_name == "YomaControlServer"
    assert config.display_name == "YOMA Control Server"
    assert config.start_type == "auto"


def test_configuration_is_immutable():
    config = WindowsServiceConfiguration()

    with pytest.raises(AttributeError):
        config.service_name = "other"


def test_configuration_serialization():
    config = WindowsServiceConfiguration(
        service_name="YomaEnterprise",
        display_name="YOMA Enterprise",
        description="Enterprise YOMA background service.",
        start_type="manual",
    )

    assert config.as_dict() == {
        "service_name": "YomaEnterprise",
        "display_name": "YOMA Enterprise",
        "description": "Enterprise YOMA background service.",
        "start_type": "manual",
    }


@pytest.mark.parametrize("start_type", ["auto", "manual", "disabled"])
def test_supported_start_types(start_type):
    config = WindowsServiceConfiguration(start_type=start_type)

    assert config.start_type == start_type


def test_invalid_start_type_rejected():
    with pytest.raises(ValueError):
        WindowsServiceConfiguration(start_type="automatic")


@pytest.mark.parametrize(
    "field",
    ["service_name", "display_name", "description"],
)
def test_required_metadata_rejects_empty_values(field):
    values = {
        "service_name": "YomaControlServer",
        "display_name": "YOMA Control Server",
        "description": "YOMA service",
        "start_type": "auto",
    }
    values[field] = ""

    with pytest.raises(ValueError):
        WindowsServiceConfiguration(**values)


def test_service_metadata_matches_existing_windows_service():
    from yoma.office.control_server.windows_service.service import (
        YomaWindowsService,
    )

    config = WindowsServiceConfiguration()

    assert config.service_name == YomaWindowsService._svc_name_
    assert config.display_name == YomaWindowsService._svc_display_name_
    assert config.description == YomaWindowsService._svc_description_


def test_default_configuration_is_background_service():
    config = WindowsServiceConfiguration()

    assert config.start_type == "auto"
    assert "background" in config.description.lower()


def test_configuration_contains_no_secret_material():
    config = WindowsServiceConfiguration()

    data = config.as_dict()

    assert "password" not in data
    assert "secret" not in data
    assert "api_key" not in data
    assert "credential" not in data


def test_configuration_does_not_grant_execution_authority():
    config = WindowsServiceConfiguration()

    assert not hasattr(config, "execute")
    assert not hasattr(config, "authorize")
    assert not hasattr(config, "approval")
