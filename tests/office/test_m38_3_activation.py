from datetime import datetime, timezone

import pytest

from yoma.office.licensing.activation import (
    ActivationResult,
    ActivationStatus,
    LicenseActivationRuntime,
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
        "edition": ProductEdition.PROFESSIONAL,
        "status": LicenseStatus.ACTIVE,
        "issued_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "entitlements": {"gmail": True},
    }
    values.update(overrides)
    return YomaLicense(**values)


def test_initial_state_is_inactive():
    runtime = LicenseActivationRuntime()

    assert runtime.status is ActivationStatus.INACTIVE
    assert runtime.is_active is False


def test_valid_license_can_be_activated():
    runtime = LicenseActivationRuntime()

    result = runtime.activate(make_license(), now=NOW)

    assert result.status is ActivationStatus.ACTIVE
    assert result.changed is True
    assert result.reason == "activation_successful"
    assert runtime.is_active is True


def test_activation_records_timestamp():
    runtime = LicenseActivationRuntime()

    result = runtime.activate(make_license(), now=NOW)

    assert result.activated_at == NOW


def test_activation_preserves_license_identity():
    runtime = LicenseActivationRuntime()

    result = runtime.activate(make_license(), now=NOW)

    assert result.license_id == "LIC-001"
    assert result.organization_id == "ORG-001"


def test_duplicate_activation_is_idempotent():
    runtime = LicenseActivationRuntime()
    license = make_license()

    first = runtime.activate(license, now=NOW)
    second = runtime.activate(license, now=NOW)

    assert first.changed is True
    assert second.changed is False
    assert second.reason == "already_active"
    assert second.status is ActivationStatus.ACTIVE


@pytest.mark.parametrize(
    "status",
    [
        LicenseStatus.EXPIRED,
        LicenseStatus.REVOKED,
        LicenseStatus.SUSPENDED,
    ],
)
def test_invalid_license_cannot_be_activated(status):
    runtime = LicenseActivationRuntime()

    result = runtime.activate(
        make_license(status=status),
        now=NOW,
    )

    assert result.changed is False
    assert runtime.is_active is False
    assert result.reason.startswith("activation_rejected:")


def test_expired_license_cannot_be_activated():
    runtime = LicenseActivationRuntime()

    result = runtime.activate(
        make_license(
            expires_at=datetime(2026, 5, 1, tzinfo=timezone.utc)
        ),
        now=NOW,
    )

    assert result.changed is False
    assert runtime.is_active is False
    assert result.reason == "activation_rejected:license_expired"


def test_activation_requires_timezone_aware_now():
    runtime = LicenseActivationRuntime()

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        runtime.activate(
            make_license(),
            now=datetime(2026, 6, 1),
        )


def test_deactivation_changes_active_state():
    runtime = LicenseActivationRuntime()

    runtime.activate(make_license(), now=NOW)
    result = runtime.deactivate(now=NOW)

    assert result.changed is True
    assert result.status is ActivationStatus.DEACTIVATED
    assert runtime.is_active is False


def test_deactivation_preserves_identity_in_result():
    runtime = LicenseActivationRuntime()

    runtime.activate(make_license(), now=NOW)
    result = runtime.deactivate(now=NOW)

    assert result.license_id == "LIC-001"
    assert result.organization_id == "ORG-001"


def test_repeated_deactivation_is_safe():
    runtime = LicenseActivationRuntime()

    runtime.activate(make_license(), now=NOW)
    first = runtime.deactivate(now=NOW)
    second = runtime.deactivate(now=NOW)

    assert first.changed is True
    assert second.changed is False
    assert second.reason == "already_inactive"


def test_activation_result_is_immutable():
    runtime = LicenseActivationRuntime()

    result = runtime.activate(make_license(), now=NOW)

    with pytest.raises(AttributeError):
        result.changed = False


def test_activation_result_contains_no_execution_authority():
    runtime = LicenseActivationRuntime()

    result = runtime.activate(make_license(), now=NOW)

    assert not hasattr(result, "execute")
    assert not hasattr(result, "executable")
    assert not hasattr(result, "authorized")


def test_reset_returns_runtime_to_initial_state():
    runtime = LicenseActivationRuntime()

    runtime.activate(make_license(), now=NOW)
    runtime.reset()

    assert runtime.status is ActivationStatus.INACTIVE
    assert runtime.is_active is False


def test_different_license_can_replace_previous_activation():
    runtime = LicenseActivationRuntime()

    runtime.activate(make_license(), now=NOW)

    replacement = make_license(
        license_id="LIC-002",
        organization_id="ORG-002",
    )

    result = runtime.activate(replacement, now=NOW)

    assert result.changed is True
    assert result.license_id == "LIC-002"
    assert result.organization_id == "ORG-002"
    assert runtime.is_active is True


def test_activation_is_deterministic_for_same_initial_state():
    first_runtime = LicenseActivationRuntime()
    second_runtime = LicenseActivationRuntime()

    first = first_runtime.activate(make_license(), now=NOW)
    second = second_runtime.activate(make_license(), now=NOW)

    assert first == second


def test_activation_does_not_mutate_license():
    license = make_license()

    LicenseActivationRuntime().activate(license, now=NOW)

    assert license.license_id == "LIC-001"
    assert license.organization_id == "ORG-001"
    assert license.status is LicenseStatus.ACTIVE


def test_deactivation_without_activation_is_safe():
    runtime = LicenseActivationRuntime()

    result = runtime.deactivate(now=NOW)

    assert isinstance(result, ActivationResult)
    assert result.changed is False
    assert result.status is ActivationStatus.INACTIVE
