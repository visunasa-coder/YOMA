from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.licensing.trial_subscription import (
    TrialSubscriptionManager,
    TrialSubscriptionState,
)


BASE = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def make_manager():
    return TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=BASE,
    )


def test_trial_is_14_days():
    manager = make_manager()

    trial = manager.start_trial()

    assert trial.state == TrialSubscriptionState.TRIAL
    assert trial.expires_at == BASE + timedelta(days=14)


def test_trial_is_active_before_expiry():
    manager = make_manager()
    manager.start_trial()

    status = manager.status(
        now=BASE + timedelta(days=13, hours=23)
    )

    assert status.trial is True
    assert status.active is True
    assert status.expired is False


def test_trial_expires_after_14_days():
    manager = make_manager()
    manager.start_trial()

    status = manager.status(
        now=BASE + timedelta(days=14)
    )

    assert status.state == TrialSubscriptionState.EXPIRED
    assert status.active is False
    assert status.expired is True


def test_expired_trial_requires_notification():
    manager = make_manager()
    manager.start_trial()

    message = manager.notification(
        now=BASE + timedelta(days=14)
    )

    assert message is not None
    assert "Trial Expired" in message


def test_no_notification_before_expiry():
    manager = make_manager()
    manager.start_trial()

    assert manager.notification(
        now=BASE + timedelta(days=7)
    ) is None


def test_expired_trial_cannot_run_yoma():
    manager = make_manager()
    manager.start_trial()

    assert manager.can_run_yoma(
        now=BASE + timedelta(days=14)
    ) is False


def test_trial_can_run_yoma():
    manager = make_manager()
    manager.start_trial()

    assert manager.can_run_yoma(
        now=BASE + timedelta(days=1)
    ) is True


def test_paid_activation_reactivates_yoma():
    manager = make_manager()
    manager.start_trial()

    manager.status(now=BASE + timedelta(days=14))

    subscription = manager.activate_subscription(
        activated_at=BASE + timedelta(days=14),
        duration_days=30,
    )

    assert subscription.state == TrialSubscriptionState.ACTIVE

    assert manager.can_run_yoma(
        now=BASE + timedelta(days=14, hours=1)
    ) is True


def test_subscription_expires_after_paid_period():
    manager = make_manager()

    manager.activate_subscription(
        activated_at=BASE,
        duration_days=30,
    )

    status = manager.status(
        now=BASE + timedelta(days=30)
    )

    assert status.state == TrialSubscriptionState.ACTIVE


def test_renewal_after_expiry_reactivates():
    manager = make_manager()

    manager.activate_subscription(
        activated_at=BASE,
        duration_days=30,
    )

    manager.renew_subscription(
        renewed_at=BASE + timedelta(days=30),
        duration_days=30,
    )

    assert manager.can_run_yoma(
        now=BASE + timedelta(days=30, hours=1)
    ) is True


def test_subscription_is_scoped_to_deployment():
    manager = make_manager()
    trial = manager.start_trial()

    assert trial.organization_id == "jeevan-tech"
    assert trial.deployment_id == "pilot-001"


def test_status_is_secret_free():
    manager = make_manager()
    manager.start_trial()

    data = manager.status().as_dict()

    assert "password" not in str(data).lower()
    assert "token" not in str(data).lower()
    assert data["organization_id"] == "jeevan-tech"


def test_execution_is_never_enabled():
    manager = make_manager()

    manager.start_trial()

    assert manager.status().executable is False

    manager.activate_subscription()

    assert manager.status().executable is False


def test_invalid_duration_rejected():
    manager = make_manager()

    with pytest.raises(ValueError):
        manager.activate_subscription(duration_days=0)


def test_timezone_is_required():
    manager = TrialSubscriptionManager(
        organization_id="org",
        deployment_id="dep",
        now=BASE,
    )

    with pytest.raises(ValueError):
        manager.start_trial(
            started_at=datetime(2026, 1, 1, 10, 0)
        )


def test_suspend_disables_yoma():
    manager = make_manager()
    manager.activate_subscription()

    manager.suspend()

    assert manager.can_run_yoma() is False
    assert manager.status().state == TrialSubscriptionState.SUSPENDED


def test_trial_can_be_serialized():
    manager = make_manager()
    trial = manager.start_trial()

    data = trial.as_dict()

    assert data["state"] == "trial"
    assert data["organization_id"] == "jeevan-tech"


def test_expiry_does_not_affect_customer_systems():
    manager = make_manager()
    manager.start_trial()

    status = manager.status(
        now=BASE + timedelta(days=14)
    )

    assert status.expired is True
    assert status.executable is False


def test_trial_remaining_time():
    manager = make_manager()
    manager.start_trial()

    status = manager.status(
        now=BASE + timedelta(days=7)
    )

    assert status.remaining_seconds == 7 * 24 * 60 * 60


def test_trial_state_transition_is_deterministic():
    manager = make_manager()
    manager.start_trial()

    first = manager.status(
        now=BASE + timedelta(days=14)
    )

    second = manager.status(
        now=BASE + timedelta(days=14)
    )

    assert first.state == second.state == TrialSubscriptionState.EXPIRED


def test_trial_bridges_to_m38_license():
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.license_model import LicenseStatus, ProductEdition
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)
    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )

    manager.start_trial(started_at=now)

    license = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=now,
    )

    assert license.organization_id == "jeevan-tech"
    assert license.status is LicenseStatus.ACTIVE
    assert license.edition is ProductEdition.PROFESSIONAL
    assert license.expires_at == now + timedelta(days=14)


def test_expired_trial_bridges_to_expired_license():
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.license_model import LicenseStatus
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)
    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )

    manager.start_trial(started_at=now)

    license = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=now + timedelta(days=14),
    )

    assert license.status is LicenseStatus.EXPIRED


def test_trial_license_integrates_with_licensing_runtime(tmp_path):
    from datetime import datetime, timezone
    from yoma.office.licensing.license_model import LicenseStatus
    from yoma.office.licensing.persistence import LicensePersistence
    from yoma.office.licensing.runtime import LicensingRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    license = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=now,
    )

    persistence = LicensePersistence(tmp_path / "license.db")
    runtime = LicensingRuntime(persistence)

    result = runtime.activate(
        license,
        now=now,
    )

    assert license.status is LicenseStatus.ACTIVE
    assert result.validation.valid is True
    assert result.active is True


def test_expired_trial_is_rejected_by_licensing_runtime(tmp_path):
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.persistence import LicensePersistence
    from yoma.office.licensing.runtime import LicensingRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    license = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=now + timedelta(days=14),
    )

    runtime = LicensingRuntime(
        LicensePersistence(tmp_path / "license.db")
    )

    result = runtime.activate(
        license,
        now=now + timedelta(days=14),
    )

    assert result.validation.valid is False
    assert result.active is False
    assert "license_status:expired" in result.validation.reason



def test_expired_trial_blocks_yoma_capability(tmp_path):
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.persistence import LicensePersistence
    from yoma.office.licensing.runtime import LicensingRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    expired_license = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=now + timedelta(days=14),
    )

    runtime = LicensingRuntime(
        LicensePersistence(tmp_path / "license.db")
    )

    decision = runtime.check(
        expired_license,
        "yoma",
        now=now + timedelta(days=14),
    )

    assert decision.allowed is False
    assert decision.executable is False
    assert decision.requires_human_approval is True
    assert decision.reason == "license_invalid:license_status:expired"


def test_active_trial_allows_entitled_yoma_capability(tmp_path):
    from datetime import datetime, timezone
    from yoma.office.licensing.persistence import LicensePersistence
    from yoma.office.licensing.runtime import LicensingRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    active_license = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=now,
    )

    runtime = LicensingRuntime(
        LicensePersistence(tmp_path / "license.db")
    )

    decision = runtime.check(
        active_license,
        "yoma",
        now=now,
    )

    assert decision.allowed is True
    assert decision.executable is False
    assert decision.requires_human_approval is True

def test_expired_trial_requires_notification():
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    expiry = now + timedelta(days=14)

    status = manager.status(now=expiry)
    notification = manager.notification(now=expiry)

    assert status.expired is True
    assert status.active is False
    assert status.trial is False
    assert status.notification_required is True
    assert status.executable is False
    assert notification is not None
    assert "Trial Expired" in notification
    assert "activate your subscription" in notification


def test_active_trial_has_no_expiry_notification():
    from datetime import datetime, timezone
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    status = manager.status(now=now)
    notification = manager.notification(now=now)

    assert status.active is True
    assert status.expired is False
    assert status.notification_required is False
    assert notification is None

def test_active_trial_has_no_expiry_notification():
    from datetime import datetime, timezone
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    status = manager.status(now=now)
    notification = manager.notification(now=now)

    assert status.active is True
    assert status.expired is False
    assert status.trial is True
    assert status.notification_required is False
    assert status.executable is False
    assert notification is None

def test_expired_trial_can_be_reactivated_without_reinstall():
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.license_model import LicenseStatus
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )

    manager.start_trial(started_at=now)

    expired_at = now + timedelta(days=14)

    expired = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=expired_at,
    )

    assert expired.status is LicenseStatus.EXPIRED
    assert manager.can_run_yoma(now=expired_at) is False

    activated_at = expired_at + timedelta(minutes=5)

    subscription = manager.activate_subscription(
        activated_at=activated_at,
        duration_days=30,
    )

    assert subscription.state.value == "active"
    assert manager.can_run_yoma(now=activated_at) is True

    reactivated = manager.to_yoma_license(
        license_id="YOMA-JEEVAN-001",
        now=activated_at,
    )

    assert reactivated.status is LicenseStatus.ACTIVE
    assert reactivated.license_id == expired.license_id
    assert reactivated.organization_id == expired.organization_id

def test_trial_subscription_persistence_round_trip(tmp_path):
    from datetime import datetime, timezone
    from yoma.office.licensing.trial_persistence import TrialSubscriptionPersistence
    from yoma.office.licensing.trial_subscription import (
        TrialSubscriptionManager,
        TrialSubscriptionState,
    )

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )

    subscription = manager.start_trial(started_at=now)

    persistence = TrialSubscriptionPersistence(
        tmp_path / "trial.json"
    )

    persistence.save(subscription)

    recovered = persistence.load()

    assert recovered is not None
    assert recovered.organization_id == "jeevan-tech"
    assert recovered.deployment_id == "pilot-001"
    assert recovered.started_at == subscription.started_at
    assert recovered.expires_at == subscription.expires_at
    assert recovered.state is TrialSubscriptionState.TRIAL
    assert recovered.edition == subscription.edition


def test_subscription_persistence_survives_expired_state(tmp_path):
    from datetime import datetime, timezone, timedelta
    from yoma.office.licensing.trial_persistence import TrialSubscriptionPersistence
    from yoma.office.licensing.trial_subscription import (
        TrialSubscriptionManager,
        TrialSubscriptionState,
    )

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )

    manager.start_trial(started_at=now)

    expired = manager.refresh(
        now=now + timedelta(days=14)
    )

    persistence = TrialSubscriptionPersistence(
        tmp_path / "trial.json"
    )

    persistence.save(expired)

    recovered = persistence.load()

    assert recovered is not None
    assert recovered.state is TrialSubscriptionState.EXPIRED
    assert recovered.expires_at == expired.expires_at


def test_subscription_persistence_recovers_paid_subscription(tmp_path):
    from datetime import datetime, timezone
    from yoma.office.licensing.trial_persistence import TrialSubscriptionPersistence
    from yoma.office.licensing.trial_subscription import (
        TrialSubscriptionManager,
        TrialSubscriptionState,
    )

    now = datetime(2026, 9, 20, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )

    subscription = manager.activate_subscription(
        activated_at=now,
        duration_days=30,
    )

    persistence = TrialSubscriptionPersistence(
        tmp_path / "subscription.json"
    )

    persistence.save(subscription)

    recovered = persistence.load()

    assert recovered is not None
    assert recovered.state is TrialSubscriptionState.ACTIVE
    assert recovered.started_at == subscription.started_at
    assert recovered.expires_at == subscription.expires_at


def test_corrupt_trial_persistence_fails_closed(tmp_path):
    from yoma.office.licensing.trial_persistence import TrialSubscriptionPersistence

    path = tmp_path / "trial.json"
    path.write_text("{not-valid-json", encoding="utf-8")

    persistence = TrialSubscriptionPersistence(path)

    assert persistence.load() is None


def test_embedded_runtime_blocks_expired_trial():
    from datetime import datetime, timezone, timedelta
    from yoma.office.runtime import YomaEmbeddedRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    runtime = YomaEmbeddedRuntime(
        trial_subscription=manager,
    )

    manager.refresh(now=now + timedelta(days=14))

    runtime.start()

    assert runtime.running is False
    assert runtime.license_blocked is True
    assert runtime.license_notification is not None
    assert runtime.status().runtime_state == "license_expired"


def test_embedded_runtime_starts_during_active_trial():
    from datetime import datetime, timezone
    from yoma.office.runtime import YomaEmbeddedRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    runtime = YomaEmbeddedRuntime(
        trial_subscription=manager,
    )

    runtime.start()

    try:
        assert runtime.running is True
        assert runtime.license_blocked is False
        assert runtime.status().runtime_state == "running"
    finally:
        runtime.stop()


def test_embedded_runtime_can_resume_after_subscription_activation():
    from datetime import datetime, timezone, timedelta
    from yoma.office.runtime import YomaEmbeddedRuntime
    from yoma.office.licensing.trial_subscription import TrialSubscriptionManager

    now = datetime(2026, 9, 6, tzinfo=timezone.utc)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-001",
        now=now,
    )
    manager.start_trial(started_at=now)

    manager.refresh(now=now + timedelta(days=14))

    runtime = YomaEmbeddedRuntime(
        trial_subscription=manager,
    )

    runtime.start()

    assert runtime.running is False
    assert runtime.license_blocked is True

    manager.activate_subscription(
        activated_at=now + timedelta(days=14, minutes=5),
        duration_days=30,
    )

    runtime.start()

    try:
        assert runtime.running is True
        assert runtime.license_blocked is False
        assert runtime.status().runtime_state == "running"
    finally:
        runtime.stop()
