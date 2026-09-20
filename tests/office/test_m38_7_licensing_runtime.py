from datetime import datetime, timezone

import pytest

from yoma.office.licensing.activation import ActivationStatus
from yoma.office.licensing.license_model import (
    LicenseStatus,
    ProductEdition,
    YomaLicense,
)
from yoma.office.licensing.persistence import (
    LicensePersistence,
    PersistedActivation,
)
from yoma.office.licensing.runtime import (
    LicensingRuntime,
    LicensingRuntimeResult,
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


def make_runtime(tmp_path):
    return LicensingRuntime(
        LicensePersistence(tmp_path / "license.json")
    )


def test_runtime_activate_returns_unified_result(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert isinstance(result, LicensingRuntimeResult)


def test_runtime_validates_license(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert result.validation.valid is True


def test_runtime_activates_valid_license(tmp_path):
    runtime = make_runtime(tmp_path)

    result = runtime.activate(make_license(), now=NOW)

    assert result.activation.status is ActivationStatus.ACTIVE
    assert result.active is True


def test_runtime_persists_activation(tmp_path):
    runtime = make_runtime(tmp_path)

    runtime.activate(make_license(), now=NOW)

    persisted = runtime.recover()

    assert persisted is not None
    assert persisted.license_id == "LIC-001"
    assert persisted.organization_id == "ORG-001"
    assert persisted.status is ActivationStatus.ACTIVE


def test_runtime_exposes_entitled_capabilities(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert result.entitled_capabilities == (
        "calendar",
        "gmail",
    )


def test_runtime_can_check_capability(tmp_path):
    runtime = make_runtime(tmp_path)

    result = runtime.check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.allowed is True


def test_runtime_denies_unentitled_capability(tmp_path):
    runtime = make_runtime(tmp_path)

    result = runtime.check(
        make_license(),
        "advanced_analytics",
        now=NOW,
    )

    assert result.allowed is False


def test_runtime_deactivation_persists_state(tmp_path):
    runtime = make_runtime(tmp_path)

    runtime.activate(make_license(), now=NOW)
    result = runtime.deactivate(now=NOW)

    assert result.changed is True
    assert result.status is ActivationStatus.DEACTIVATED

    persisted = runtime.recover()

    assert persisted is not None
    assert persisted.status is ActivationStatus.DEACTIVATED


def test_runtime_reset_clears_state(tmp_path):
    runtime = make_runtime(tmp_path)

    runtime.activate(make_license(), now=NOW)
    runtime.reset()

    assert runtime.recover() is None
    assert runtime.activation.status is ActivationStatus.INACTIVE


def test_runtime_duplicate_activation_is_idempotent(tmp_path):
    runtime = make_runtime(tmp_path)
    license = make_license()

    first = runtime.activate(license, now=NOW)
    second = runtime.activate(license, now=NOW)

    assert first.activation.changed is True
    assert second.activation.changed is False
    assert second.activation.reason == "already_active"


def test_invalid_license_is_not_activated(tmp_path):
    runtime = make_runtime(tmp_path)

    result = runtime.activate(
        make_license(status=LicenseStatus.REVOKED),
        now=NOW,
    )

    assert result.validation.valid is False
    assert result.active is False


def test_expired_license_is_not_activated(tmp_path):
    runtime = make_runtime(tmp_path)

    result = runtime.activate(
        make_license(
            expires_at=datetime(2026, 5, 1, tzinfo=timezone.utc)
        ),
        now=NOW,
    )

    assert result.validation.valid is False
    assert result.active is False


def test_runtime_requires_timezone_aware_now(tmp_path):
    runtime = make_runtime(tmp_path)

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        runtime.activate(
            make_license(),
            now=datetime(2026, 6, 1),
        )


def test_runtime_capability_check_requires_timezone_aware_now(tmp_path):
    runtime = make_runtime(tmp_path)

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        runtime.check(
            make_license(),
            "gmail",
            now=datetime(2026, 6, 1),
        )


def test_runtime_activation_result_requires_human_approval(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert result.requires_human_approval is True


def test_runtime_activation_result_is_not_executable(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert result.executable is False


def test_runtime_access_decision_is_not_executable(tmp_path):
    result = make_runtime(tmp_path).check(
        make_license(),
        "gmail",
        now=NOW,
    )

    assert result.executable is False


def test_runtime_does_not_grant_authorization(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert not hasattr(result, "authorized")
    assert not hasattr(result.activation, "authorized")


def test_runtime_recovery_is_state_only(tmp_path):
    runtime = make_runtime(tmp_path)

    runtime.activate(make_license(), now=NOW)
    recovered = runtime.recover()

    assert isinstance(recovered, PersistedActivation)
    assert not hasattr(recovered, "execute")
    assert not hasattr(recovered, "authorized")


def test_runtime_is_deterministic(tmp_path):
    first = make_runtime(tmp_path / "one").activate(
        make_license(),
        now=NOW,
    )

    second = make_runtime(tmp_path / "two").activate(
        make_license(),
        now=NOW,
    )

    assert first == second


def test_runtime_preserves_license_identity(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(),
        now=NOW,
    )

    assert result.license_id == "LIC-001"
    assert result.organization_id == "ORG-001"


def test_runtime_empty_entitlements_have_no_access_decision(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(entitlements={}),
        now=NOW,
    )

    assert result.access is None
    assert result.entitled_capabilities == ()


def test_runtime_non_expiring_license_can_activate(tmp_path):
    result = make_runtime(tmp_path).activate(
        make_license(expires_at=None),
        now=NOW,
    )

    assert result.active is True


def test_runtime_deactivate_before_activation_is_safe(tmp_path):
    runtime = make_runtime(tmp_path)

    result = runtime.deactivate(now=NOW)

    assert result.changed is False
    assert result.status is ActivationStatus.INACTIVE


def test_runtime_has_no_direct_execution_method(tmp_path):
    runtime = make_runtime(tmp_path)

    assert not hasattr(runtime, "execute")
    assert not hasattr(runtime, "execute_action")
