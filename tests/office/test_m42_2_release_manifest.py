from yoma.office.release_manifest import (
    ReleaseComponent,
    ReleaseManifest,
)


def component(
    name="yoma-core",
    version="1.0.0",
    component_type="runtime",
    required=True,
):
    return ReleaseComponent(
        name=name,
        version=version,
        component_type=component_type,
        required=required,
    )


def manifest(**overrides):
    values = {
        "product_name": "YOMA",
        "product_version": "1.0.0",
        "release_channel": "commercial",
        "vendor_name": "VP Technologies",
        "components": (component(),),
    }
    values.update(overrides)
    return ReleaseManifest(**values)


def test_manifest_is_constructed():
    result = manifest()
    assert result.product_name == "YOMA"
    assert result.product_version == "1.0.0"


def test_component_serializes():
    result = component()
    data = result.as_dict()
    assert data["name"] == "yoma-core"
    assert data["version"] == "1.0.0"


def test_manifest_serializes():
    data = manifest().as_dict()
    assert data["product_name"] == "YOMA"
    assert data["release_channel"] == "commercial"
    assert len(data["components"]) == 1


def test_manifest_bytes_are_deterministic():
    first = manifest().manifest_bytes()
    second = manifest().manifest_bytes()
    assert first == second


def test_manifest_integrity_is_deterministic():
    first = manifest().integrity_sha256()
    second = manifest().integrity_sha256()
    assert first == second
    assert len(first) == 64


def test_component_rejects_empty_name():
    try:
        component(name="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_component_rejects_empty_version():
    try:
        component(version="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_component_rejects_empty_type():
    try:
        component(component_type="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_manifest_rejects_empty_product():
    try:
        manifest(product_name="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_manifest_rejects_non_tuple_components():
    try:
        manifest(components=[component()])
    except TypeError:
        pass
    else:
        raise AssertionError("Expected TypeError")


def test_integrity_changes_when_manifest_changes():
    first = manifest(product_version="1.0.0").integrity_sha256()
    second = manifest(product_version="1.0.1").integrity_sha256()
    assert first != second


def test_manifest_does_not_contain_secret_fields():
    assert manifest().contains_secret_fields() is False


def test_secret_named_component_is_detected():
    secret_component = component(name="api_token")
    result = manifest(components=(secret_component,))
    assert result.contains_secret_fields() is True


def test_manifest_is_secret_free_metadata():
    data = manifest().as_dict()
    assert "password" not in str(data).lower()
    assert "token" not in str(data).lower()
    assert "secret" not in str(data).lower()


def test_required_component_flag_is_preserved():
    result = component(required=False)
    assert result.required is False


def test_manifest_version_is_explicit():
    assert manifest().manifest_version == "1"
