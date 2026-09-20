from yoma.office.production_release_identity import (
    ProductionReleaseIdentity,
    ProductionReleaseIdentityValidator,
)


def test_default_identity_is_yoma_v1():
    identity = ProductionReleaseIdentity()
    assert identity.product_name == "YOMA"
    assert identity.version == "1.0.0"


def test_release_name_is_yoma_v1():
    identity = ProductionReleaseIdentity()
    assert identity.release_name == "YOMA v1.0"


def test_production_channel_is_explicit():
    identity = ProductionReleaseIdentity()
    assert identity.release_channel == "production"
    assert identity.is_production is True


def test_v1_identity_is_explicit():
    identity = ProductionReleaseIdentity()
    assert identity.is_v1 is True


def test_vendor_is_vp_technologies():
    identity = ProductionReleaseIdentity()
    assert identity.vendor_name == "VP Technologies"


def test_initial_release_status_is_candidate():
    identity = ProductionReleaseIdentity()
    assert identity.release_status == "candidate"


def test_identity_serializes():
    data = ProductionReleaseIdentity().as_dict()
    assert data["product_name"] == "YOMA"
    assert data["version"] == "1.0.0"
    assert data["release_channel"] == "production"


def test_empty_product_is_rejected():
    try:
        ProductionReleaseIdentity(product_name="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_empty_version_is_rejected():
    try:
        ProductionReleaseIdentity(version="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_validator_accepts_default_identity():
    identity = ProductionReleaseIdentity()
    assert ProductionReleaseIdentityValidator().validate(identity) is True


def test_non_v1_identity_is_rejected():
    identity = ProductionReleaseIdentity(version="2.0.0")
    assert ProductionReleaseIdentityValidator().validate(identity) is False


def test_non_production_channel_is_rejected():
    identity = ProductionReleaseIdentity(release_channel="beta")
    assert ProductionReleaseIdentityValidator().validate(identity) is False


def test_wrong_product_is_rejected():
    identity = ProductionReleaseIdentity(product_name="OTHER")
    assert ProductionReleaseIdentityValidator().validate(identity) is False


def test_identity_is_deterministic():
    first = ProductionReleaseIdentity()
    second = ProductionReleaseIdentity()
    assert first == second
