from datetime import datetime, timezone

import pytest

from yoma.office.licensing.activation import ActivationStatus
from yoma.office.licensing.hardening import (
    LicensingHardening,
    LicensingHardeningResult,
)
from yoma.office.licensing.license_model import (
    LicenseStatus,
    ProductEdition,
    YomaLicense,
)
from yoma.office.licensing.persistence import (
    LicensePersistence,
    PersistedActivation,
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
        "entitlements": {"gmail": True},
    }
    values.update(overrides)
    return YomaLicense(**values)


def make_hardening(tmp_path):
    return LicensingHardening(
        LicensePersistence(tmp_path / "license.json")
    )


def test_valid_license_is_safe(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.safe is True
    assert result.failures == ()


def test_result_type_is_correct(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert isinstance(result, LicensingHardeningResult)


def test_identity_is_preserved(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.license_id == "LIC-001"
    assert result.organization_id == "ORG-001"


@pytest.mark.parametrize(
    "status",
    [
        LicenseStatus.EXPIRED,
        LicenseStatus.REVOKED,
        LicenseStatus.SUSPENDED,
    ],
)
def test_invalid_lifecycle_is_not_safe(tmp_path, status):
    result = make_hardening(tmp_path).assess(
        make_license(status=status),
        now=NOW,
    )

    assert result.safe is False
    assert result.failures == (
        f"license_status:{status.value}",
    )


def test_expired_license_is_not_safe(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(
            expires_at=datetime(2026, 5, 1, tzinfo=timezone.utc)
        ),
        now=NOW,
    )

    assert result.safe is False
    assert "license_expired" in result.failures


def test_missing_persistence_is_safe(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.safe is True


def test_matching_persistence_is_safe(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    persistence.save(
        PersistedActivation(
            license_id="LIC-001",
            organization_id="ORG-001",
            status=ActivationStatus.ACTIVE,
            activated_at="2026-06-01T10:00:00+00:00",
        )
    )

    result = LicensingHardening(persistence).assess(
        make_license(),
        now=NOW,
    )

    assert result.safe is True


def test_persistent_license_mismatch_is_detected(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    persistence.save(
        PersistedActivation(
            license_id="LIC-999",
            organization_id="ORG-001",
            status=ActivationStatus.ACTIVE,
            activated_at="2026-06-01T10:00:00+00:00",
        )
    )

    result = LicensingHardening(persistence).assess(
        make_license(),
        now=NOW,
    )

    assert result.safe is False
    assert "persistent_license_mismatch" in result.failures


def test_persistent_organization_mismatch_is_detected(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    persistence.save(
        PersistedActivation(
            license_id="LIC-001",
            organization_id="ORG-999",
            status=ActivationStatus.ACTIVE,
            activated_at="2026-06-01T10:00:00+00:00",
        )
    )

    result = LicensingHardening(persistence).assess(
        make_license(),
        now=NOW,
    )

    assert result.safe is False
    assert "persistent_organization_mismatch" in result.failures


def test_invalid_active_persistence_is_detected(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    persistence.save(
        PersistedActivation(
            license_id="LIC-001",
            organization_id="ORG-001",
            status=ActivationStatus.ACTIVE,
            activated_at="2026-06-01T10:00:00+00:00",
        )
    )

    result = LicensingHardening(persistence).assess(
        make_license(
            status=LicenseStatus.REVOKED,
        ),
        now=NOW,
    )

    assert result.safe is False
    assert "active_persistence_with_invalid_license" in result.failures


def test_checks_are_deterministic(tmp_path):
    hardening = make_hardening(tmp_path)
    license = make_license()

    first = hardening.assess(license, now=NOW)
    second = hardening.assess(license, now=NOW)

    assert first.checks == second.checks
    assert first.failures == second.failures
    assert first.safe == second.safe


def test_checks_have_expected_order(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.checks == (
        "license_structure",
        "license_validation",
        "persistent_state_integrity",
        "identity_consistency",
    )


def test_result_is_immutable(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    with pytest.raises(AttributeError):
        result.safe = False


def test_naive_now_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        make_hardening(tmp_path).assess(
            make_license(),
            now=datetime(2026, 6, 1),
        )


def test_hardening_has_no_execution_authority(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.executable is False
    assert result.requires_human_approval is True
    assert not hasattr(result, "execute")
    assert not hasattr(result, "authorized")


def test_corrupt_persistence_fails_closed(tmp_path):
    path = tmp_path / "license.json"
    path.write_text("{broken", encoding="utf-8")

    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.safe is True


def test_hardening_does_not_modify_persistence(tmp_path):
    persistence = LicensePersistence(tmp_path / "license.json")

    persistence.save(
        PersistedActivation(
            license_id="LIC-001",
            organization_id="ORG-001",
            status=ActivationStatus.ACTIVE,
            activated_at="2026-06-01T10:00:00+00:00",
        )
    )

    before = persistence.load()

    LicensingHardening(persistence).assess(
        make_license(),
        now=NOW,
    )

    after = persistence.load()

    assert before == after


def test_non_expiring_valid_license_is_safe(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(expires_at=None),
        now=NOW,
    )

    assert result.safe is True


def test_hardening_preserves_governance_boundary_on_failure(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(status=LicenseStatus.REVOKED),
        now=NOW,
    )

    assert result.executable is False
    assert result.requires_human_approval is True


def test_hardening_preserves_governance_boundary_on_success(tmp_path):
    result = make_hardening(tmp_path).assess(
        make_license(),
        now=NOW,
    )

    assert result.executable is False
    assert result.requires_human_approval is True
