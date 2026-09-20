from datetime import datetime, timezone

import pytest

from yoma.office.licensing.entitlements import (
    EntitlementResult,
    LicenseEntitlementResolver,
)
from yoma.office.licensing.license_model import (
    LicenseStatus,
    ProductEdition,
    YomaLicense,
)


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


def test_entitled_capability_returns_true():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "gmail",
    )

    assert result.entitled is True
    assert result.reason == "capability_entitled"


def test_non_entitled_capability_returns_false():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "advanced_analytics",
    )

    assert result.entitled is False
    assert result.reason == "capability_not_entitled"


def test_missing_capability_returns_false():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "missing_feature",
    )

    assert result.entitled is False
    assert result.reason == "capability_not_entitled"


def test_result_contains_capability():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "gmail",
    )

    assert result.capability == "gmail"


def test_result_contains_edition():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "gmail",
    )

    assert result.edition is ProductEdition.ENTERPRISE


def test_result_is_immutable():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "gmail",
    )

    with pytest.raises(AttributeError):
        result.entitled = False


def test_invalid_license_type_is_rejected():
    with pytest.raises(TypeError, match="license must be a YomaLicense"):
        LicenseEntitlementResolver().resolve(
            "invalid",
            "gmail",
        )


def test_empty_capability_is_rejected():
    with pytest.raises(ValueError, match="capability must not be empty"):
        LicenseEntitlementResolver().resolve(
            make_license(),
            " ",
        )


def test_resolve_many_returns_results_in_input_order():
    results = LicenseEntitlementResolver().resolve_many(
        make_license(),
        ["calendar", "gmail", "advanced_analytics"],
    )

    assert [result.capability for result in results] == [
        "calendar",
        "gmail",
        "advanced_analytics",
    ]


def test_resolve_many_returns_correct_entitlements():
    results = LicenseEntitlementResolver().resolve_many(
        make_license(),
        ["calendar", "gmail", "advanced_analytics"],
    )

    assert [result.entitled for result in results] == [
        True,
        True,
        False,
    ]


def test_resolve_many_is_immutable_tuple():
    results = LicenseEntitlementResolver().resolve_many(
        make_license(),
        ["gmail", "calendar"],
    )

    assert isinstance(results, tuple)


def test_empty_capability_list_returns_empty_tuple():
    results = LicenseEntitlementResolver().resolve_many(
        make_license(),
        [],
    )

    assert results == ()


def test_entitled_capabilities_are_sorted():
    result = LicenseEntitlementResolver().entitled_capabilities(
        make_license()
    )

    assert result == ("calendar", "gmail")


def test_false_entitlements_are_excluded():
    result = LicenseEntitlementResolver().entitled_capabilities(
        make_license()
    )

    assert "advanced_analytics" not in result


def test_entitled_capabilities_returns_tuple():
    result = LicenseEntitlementResolver().entitled_capabilities(
        make_license()
    )

    assert isinstance(result, tuple)


def test_empty_entitlements_return_empty_tuple():
    result = LicenseEntitlementResolver().entitled_capabilities(
        make_license(entitlements={})
    )

    assert result == ()


def test_entitlement_resolution_does_not_mutate_license():
    license = make_license()

    LicenseEntitlementResolver().resolve_many(
        license,
        ["gmail", "calendar"],
    )

    assert license.entitlements == {
        "gmail": True,
        "calendar": True,
        "advanced_analytics": False,
    }


def test_entitlement_result_contains_no_execution_authority():
    result = LicenseEntitlementResolver().resolve(
        make_license(),
        "gmail",
    )

    assert not hasattr(result, "execute")
    assert not hasattr(result, "executable")
    assert not hasattr(result, "authorized")


def test_entitlement_resolution_is_deterministic():
    resolver = LicenseEntitlementResolver()
    license = make_license()

    first = resolver.entitled_capabilities(license)
    second = resolver.entitled_capabilities(license)

    assert first == second


def test_different_editions_preserve_their_identity():
    resolver = LicenseEntitlementResolver()

    community = resolver.resolve(
        make_license(edition=ProductEdition.COMMUNITY),
        "gmail",
    )
    professional = resolver.resolve(
        make_license(edition=ProductEdition.PROFESSIONAL),
        "gmail",
    )

    assert community.edition is ProductEdition.COMMUNITY
    assert professional.edition is ProductEdition.PROFESSIONAL
