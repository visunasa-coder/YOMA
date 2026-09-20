from datetime import datetime, timezone

import pytest

from yoma.office.licensing.license_model import (
    LicenseStatus,
    ProductEdition,
    YomaLicense,
)
from yoma.office.licensing.license_validation import (
    LicenseValidationResult,
    LicenseValidator,
)


def make_license(**overrides):
    values = {
        "license_id": "LIC-001",
        "organization_id": "ORG-001",
        "edition": ProductEdition.PROFESSIONAL,
        "status": LicenseStatus.ACTIVE,
        "issued_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "entitlements": {"gmail": True},
    }
    values.update(overrides)
    return YomaLicense(**values)


NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_active_license_is_valid():
    result = LicenseValidator().validate(make_license(), now=NOW)

    assert result.valid is True
    assert result.reason == "license_valid"


def test_validation_returns_license_identity():
    result = LicenseValidator().validate(make_license(), now=NOW)

    assert result.license_id == "LIC-001"
    assert result.organization_id == "ORG-001"


def test_validation_result_is_immutable():
    result = LicenseValidator().validate(make_license(), now=NOW)

    with pytest.raises(AttributeError):
        result.valid = False


@pytest.mark.parametrize(
    "status",
    [
        LicenseStatus.EXPIRED,
        LicenseStatus.REVOKED,
        LicenseStatus.SUSPENDED,
    ],
)
def test_non_active_license_is_invalid(status):
    result = LicenseValidator().validate(
        make_license(status=status),
        now=NOW,
    )

    assert result.valid is False
    assert result.reason == f"license_status:{status.value}"


def test_expired_active_license_is_invalid():
    result = LicenseValidator().validate(
        make_license(
            expires_at=datetime(2026, 5, 1, tzinfo=timezone.utc)
        ),
        now=NOW,
    )

    assert result.valid is False
    assert result.reason == "license_expired"


def test_license_at_exact_expiration_is_invalid():
    expiration = datetime(2026, 6, 1, tzinfo=timezone.utc)

    result = LicenseValidator().validate(
        make_license(expires_at=expiration),
        now=expiration,
    )

    assert result.valid is False
    assert result.reason == "license_expired"


def test_non_expiring_active_license_is_valid():
    result = LicenseValidator().validate(
        make_license(expires_at=None),
        now=NOW,
    )

    assert result.valid is True


def test_timezone_naive_now_is_rejected():
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        LicenseValidator().validate(
            make_license(),
            now=datetime(2026, 6, 1),
        )


def test_invalid_license_type_is_rejected():
    with pytest.raises(TypeError, match="license must be a YomaLicense"):
        LicenseValidator().validate("not-a-license", now=NOW)


def test_validation_is_deterministic():
    validator = LicenseValidator()
    license = make_license()

    first = validator.validate(license, now=NOW)
    second = validator.validate(license, now=NOW)

    assert first == second


def test_validation_does_not_change_license():
    license = make_license()
    before = license

    LicenseValidator().validate(license, now=NOW)

    assert license == before


def test_community_edition_can_validate():
    result = LicenseValidator().validate(
        make_license(edition=ProductEdition.COMMUNITY),
        now=NOW,
    )

    assert result.valid is True


def test_enterprise_edition_can_validate():
    result = LicenseValidator().validate(
        make_license(edition=ProductEdition.ENTERPRISE),
        now=NOW,
    )

    assert result.valid is True


def test_validation_result_contains_no_execution_authority():
    result = LicenseValidator().validate(make_license(), now=NOW)

    assert not hasattr(result, "execute")
    assert not hasattr(result, "executable")
    assert not hasattr(result, "authorized")


def test_validation_only_validates_license():
    validator = LicenseValidator()

    result = validator.validate(make_license(), now=NOW)

    assert isinstance(result, LicenseValidationResult)
    assert result.reason == "license_valid"
