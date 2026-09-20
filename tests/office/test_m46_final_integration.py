from __future__ import annotations

from datetime import datetime, timedelta, timezone

from yoma.office.control_server.windows_service.runtime import ControlServerRuntime
from yoma.office.licensing.trial_persistence import TrialSubscriptionPersistence
from yoma.office.licensing.trial_subscription import (
    TrialSubscriptionManager,
    TrialSubscriptionState,
)
from yoma.office.runtime import YomaEmbeddedRuntime


def test_m46_trial_persists_across_manager_recreation(tmp_path):
    path = tmp_path / "subscription.json"

    first = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=TrialSubscriptionPersistence(path),
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    trial = first.ensure_initialized()

    second = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=TrialSubscriptionPersistence(path),
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert second.subscription is not None
    assert second.subscription.started_at == trial.started_at
    assert second.subscription.expires_at == trial.expires_at


def test_m46_expired_persisted_trial_blocks_embedded_runtime(tmp_path):
    path = tmp_path / "subscription.json"

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=TrialSubscriptionPersistence(path),
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    manager.start_trial()

    expired = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=TrialSubscriptionPersistence(path),
        now=datetime(2026, 1, 16, tzinfo=timezone.utc),
    )

    runtime = YomaEmbeddedRuntime(
        collection_interval=3600,
        trial_subscription=expired,
    )

    runtime.start()

    assert runtime.running is False
    assert runtime.license_blocked is True
    assert runtime.license_notification is not None


def test_m46_activation_survives_recreation(tmp_path):
    path = tmp_path / "subscription.json"

    persistence = TrialSubscriptionPersistence(path)

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=persistence,
    )

    activated = manager.activate_subscription(
        activated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        duration_days=30,
    )

    recovered = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=persistence,
        now=datetime(2026, 2, 2, tzinfo=timezone.utc),
    )

    assert recovered.subscription is not None
    assert recovered.subscription.state is TrialSubscriptionState.ACTIVE
    assert recovered.subscription.expires_at == activated.expires_at


def test_m46_control_server_exposes_subscription_status(tmp_path):
    runtime = ControlServerRuntime(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        subscription_persistence_path=tmp_path / "subscription.json",
    )

    status = runtime.status()

    assert "subscription" in status
    assert status["subscription"]["organization_id"] == "jeevan-tech"
    assert status["subscription"]["deployment_id"] == "pilot-node"
    assert status["subscription"]["trial"] is True


def test_m46_expiry_is_persisted_as_expired(tmp_path):
    path = tmp_path / "subscription.json"

    manager = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=TrialSubscriptionPersistence(path),
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    manager.start_trial()

    manager.refresh(
        now=datetime(2026, 1, 15, tzinfo=timezone.utc)
    )

    restored = TrialSubscriptionManager(
        organization_id="jeevan-tech",
        deployment_id="pilot-node",
        persistence=TrialSubscriptionPersistence(path),
        now=datetime(2026, 1, 16, tzinfo=timezone.utc),
    )

    assert restored.subscription is not None
    assert restored.subscription.state is TrialSubscriptionState.EXPIRED
