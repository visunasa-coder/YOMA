from datetime import datetime, timezone

import pytest

from yoma.office.licensing.enforcement import (
    LicenseAccessDecision,
    LicenseEnforcementBoundary,
)
from yoma.office.licensing.license_model import (
    LicenseStatus,
    ProductEdition,
    YomaLicense,
)


NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def make_license(**overrides):
    values = {
        "license_id": "LIC-001",
        "organization_id": "ORG-001",
        "edition": ProductEdition.ENTERPRISE,
        "status": LicenseStatus.ACTIVE,
        "issued_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "entitlements": {
            "gmail": True,
            "calendar": True,
            "advanced_analytics": False,
        },
    }
    values.update(overrides)
    return YomaLicense(**values)


def test_entitled_capability_is_allowed():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.allowed is True
    assert result.reason == "capability_entitled"


def test_unentitled_capability_is_denied():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "advanced_analytics",
        now=NOW,
    )

    assert result.allowed is False
    assert result.reason == "capability_not_entitled"


def test_missing_capability_is_denied():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "missing_feature",
        now=NOW,
    )

    assert result.allowed is False


def test_expired_license_denies_capability():
    result = LicenseEnforcementBoundary().check(
        make_license(
            expires_at=datetime(2026, 5, 1, tzinfo=timezone.utc)
        ),
        "gmail",
        now=NOW,
    )

    assert result.allowed is False
    assert result.reason == "license_invalid:license_expired"


@pytest.mark.parametrize(
    "status",
    [
        LicenseStatus.REVOKED,
        LicenseStatus.SUSPENDED,
        LicenseStatus.EXPIRED,
    ],
)
def test_non_active_license_denies_capability(status):
    result = LicenseEnforcementBoundary().check(
        make_license(status=status),
        "gmail",
        now=NOW,
    )

    assert result.allowed is False
    assert result.reason == (
        f"license_invalid:license_status:{status.value}"
    )


def test_result_contains_license_identity():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.license_id == "LIC-001"
    assert result.organization_id == "ORG-001"


def test_result_contains_capability():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.capability == "gmail"


def test_result_is_immutable():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    with pytest.raises(AttributeError):
        result.allowed = False


def test_naive_now_is_rejected():
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        LicenseEnforcementBoundary().check(
            make_license(),
            "gmail",
            now=datetime(2026, 6, 1),
        )


def test_invalid_license_type_is_rejected():
    with pytest.raises(TypeError, match="license must be a YomaLicense"):
        LicenseEnforcementBoundary().check(
            "invalid",
            "gmail",
            now=NOW,
        )


def test_empty_capability_is_rejected():
    with pytest.raises(ValueError, match="capability must not be empty"):
        LicenseEnforcementBoundary().check(
            make_license(),
            " ",
            now=NOW,
        )


def test_license_access_does_not_grant_execution():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.allowed is True
    assert result.executable is False


def test_license_access_requires_human_approval():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.requires_human_approval is True


def test_denial_also_has_no_execution_authority():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "advanced_analytics",
        now=NOW,
    )

    assert result.executable is False
    assert result.requires_human_approval is True


def test_access_decision_has_no_execute_method():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert not hasattr(result, "execute")


def test_access_decision_has_no_authorized_field():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert not hasattr(result, "authorized")


def test_check_does_not_mutate_license():
    license = make_license()

    LicenseEnforcementBoundary().check(
        license,
        "gmail",
        now=NOW,
    )

    assert license.status is LicenseStatus.ACTIVE
    assert license.license_id == "LIC-001"


def test_check_is_deterministic():
    boundary = LicenseEnforcementBoundary()
    license = make_license()

    first = boundary.check(license, "gmail", now=NOW)
    second = boundary.check(license, "gmail", now=NOW)

    assert first == second


def test_non_expiring_license_can_allow_entitlement():
    result = LicenseEnforcementBoundary().check(
        make_license(expires_at=None),
        "gmail",
        now=NOW,
    )

    assert result.allowed is True


def test_community_edition_preserves_licensing_boundary():
    result = LicenseEnforcementBoundary().check(
        make_license(edition=ProductEdition.COMMUNITY),
        "gmail",
        now=NOW,
    )

    assert result.allowed is True
    assert result.executable is False


def test_enterprise_edition_preserves_licensing_boundary():
    result = LicenseEnforcementBoundary().check(
        make_license(edition=ProductEdition.ENTERPRISE),
        "gmail",
        now=NOW,
    )

    assert result.allowed is True
    assert result.executable is False


def test_result_type_is_correct():
    result = LicenseEnforcementBoundary().check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert isinstance(result, LicenseAccessDecision)
