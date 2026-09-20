from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.licensing.license_model import (
    LicenseStatus,
    ProductEdition,
    YomaLicense,
)


def make_license(**overrides):
    values = {
        "license_id": "LIC-001",
        "organization_id": "ORG-001",
        "edition": ProductEdition.PROFESSIONAL,
        "status": LicenseStatus.ACTIVE,
        "issued_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "entitlements": {"gmail": True, "calendar": True},
    }
    values.update(overrides)
    return YomaLicense(**values)


def test_license_model_stores_identity():
    license = make_license()

    assert license.license_id == "LIC-001"
    assert license.organization_id == "ORG-001"


def test_license_model_stores_edition_and_status():
    license = make_license()

    assert license.edition is ProductEdition.PROFESSIONAL
    assert license.status is LicenseStatus.ACTIVE


def test_license_model_requires_timezone_aware_issued_at():
    with pytest.raises(ValueError, match="issued_at must be timezone-aware"):
        make_license(issued_at=datetime(2026, 1, 1))


def test_license_model_requires_timezone_aware_expiration():
    with pytest.raises(ValueError, match="expires_at must be timezone-aware"):
        make_license(expires_at=datetime(2027, 1, 1))


def test_expiration_cannot_precede_issue():
    with pytest.raises(ValueError, match="expires_at must not precede issued_at"):
        make_license(
            issued_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
            expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_empty_license_id_is_rejected():
    with pytest.raises(ValueError, match="license_id must not be empty"):
        make_license(license_id=" ")


def test_empty_organization_id_is_rejected():
    with pytest.raises(ValueError, match="organization_id must not be empty"):
        make_license(organization_id="")


def test_active_license_is_valid_lifecycle():
    assert make_license().is_valid_lifecycle() is True


def test_non_active_license_is_not_valid_lifecycle():
    license = make_license(status=LicenseStatus.SUSPENDED)

    assert license.is_valid_lifecycle() is False


def test_license_without_expiration_does_not_expire():
    license = make_license(expires_at=None)

    assert license.is_expired(
        now=datetime(2099, 1, 1, tzinfo=timezone.utc)
    ) is False


def test_license_reports_expiration():
    license = make_license(
        expires_at=datetime(2026, 6, 1, tzinfo=timezone.utc)
    )

    assert license.is_expired(
        now=datetime(2026, 7, 1, tzinfo=timezone.utc)
    ) is True


def test_license_is_not_expired_before_expiration():
    license = make_license()

    assert license.is_expired(
        now=datetime(2026, 6, 1, tzinfo=timezone.utc)
    ) is False


def test_naive_now_is_rejected():
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        make_license().is_expired(
            now=datetime(2026, 6, 1)
        )


def test_entitlement_can_be_checked():
    license = make_license()

    assert license.has_entitlement("gmail") is True
    assert license.has_entitlement("calendar") is True


def test_missing_entitlement_is_false():
    license = make_license()

    assert license.has_entitlement("drive") is False


def test_empty_capability_is_rejected():
    with pytest.raises(ValueError, match="capability must not be empty"):
        make_license().has_entitlement(" ")


def test_license_is_immutable():
    license = make_license()

    with pytest.raises(AttributeError):
        license.license_id = "LIC-002"


def test_entitlements_are_copied_from_input():
    entitlements = {"gmail": True}
    license = make_license(entitlements=entitlements)

    entitlements["calendar"] = True

    assert license.has_entitlement("calendar") is False
