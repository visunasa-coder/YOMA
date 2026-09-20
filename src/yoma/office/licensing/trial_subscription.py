from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from .license_model import LicenseStatus, ProductEdition, YomaLicense
from .trial_persistence import TrialSubscriptionPersistence


class TrialSubscriptionState(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class TrialSubscription:
    organization_id: str
    deployment_id: str
    started_at: datetime
    expires_at: datetime
    state: TrialSubscriptionState = TrialSubscriptionState.TRIAL
    edition: str = ProductEdition.PROFESSIONAL.value

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at < self.started_at:
            raise ValueError("expires_at must not precede started_at")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    def as_dict(self) -> dict[str, object]:
        return {
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "started_at": self.started_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "state": self.state.value,
            "edition": self.edition,
        }


@dataclass(frozen=True)
class SubscriptionStatus:
    organization_id: str
    deployment_id: str
    state: TrialSubscriptionState
    active: bool
    trial: bool
    expired: bool
    remaining_seconds: int
    notification_required: bool
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "state": self.state.value,
            "active": self.active,
            "trial": self.trial,
            "expired": self.expired,
            "remaining_seconds": self.remaining_seconds,
            "notification_required": self.notification_required,
            "executable": self.executable,
        }


class TrialSubscriptionManager:
    """Manage YOMA's controlled trial and subscription lifecycle."""

    TRIAL_DAYS = 14

    def __init__(
        self,
        *,
        organization_id: str,
        deployment_id: str,
        now: datetime | None = None,
        persistence: TrialSubscriptionPersistence | None = None,
    ) -> None:
        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        self.organization_id = organization_id
        self.deployment_id = deployment_id
        self._now = current
        self.persistence = persistence
        self.subscription: TrialSubscription | None = None

        if self.persistence is not None:
            restored = self.persistence.load()

            if restored is not None:
                if (
                    restored.organization_id == organization_id
                    and restored.deployment_id == deployment_id
                ):
                    self.subscription = restored

    def _persist(self) -> None:
        if self.persistence is not None and self.subscription is not None:
            self.persistence.save(self.subscription)

    def start_trial(
        self,
        *,
        started_at: datetime | None = None,
    ) -> TrialSubscription:
        current = started_at or self._now

        if current.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")

        self.subscription = TrialSubscription(
            organization_id=self.organization_id,
            deployment_id=self.deployment_id,
            started_at=current,
            expires_at=current + timedelta(days=self.TRIAL_DAYS),
            state=TrialSubscriptionState.TRIAL,
            edition=ProductEdition.PROFESSIONAL.value,
        )

        self._persist()
        return self.subscription

    def ensure_initialized(
        self,
        *,
        started_at: datetime | None = None,
    ) -> TrialSubscription:
        if self.subscription is None:
            return self.start_trial(started_at=started_at)

        return self.refresh(now=started_at or self._now)

    def refresh(
        self,
        *,
        now: datetime | None = None,
    ) -> TrialSubscription:
        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        if self.subscription is None:
            raise RuntimeError("trial or subscription has not been initialized")

        current_subscription = self.subscription

        if (
            current_subscription.state is TrialSubscriptionState.TRIAL
            and current >= current_subscription.expires_at
        ):
            self.subscription = TrialSubscription(
                organization_id=current_subscription.organization_id,
                deployment_id=current_subscription.deployment_id,
                started_at=current_subscription.started_at,
                expires_at=current_subscription.expires_at,
                state=TrialSubscriptionState.EXPIRED,
                edition=current_subscription.edition,
            )
            self._persist()

        return self.subscription

    def activate_subscription(
        self,
        *,
        activated_at: datetime | None = None,
        duration_days: int = 30,
        edition: str = ProductEdition.PROFESSIONAL.value,
    ) -> TrialSubscription:
        current = activated_at or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("activated_at must be timezone-aware")

        if duration_days <= 0:
            raise ValueError("duration_days must be positive")

        self.subscription = TrialSubscription(
            organization_id=self.organization_id,
            deployment_id=self.deployment_id,
            started_at=current,
            expires_at=current + timedelta(days=duration_days),
            state=TrialSubscriptionState.ACTIVE,
            edition=ProductEdition(edition).value,
        )

        self._persist()
        return self.subscription

    def renew_subscription(
        self,
        *,
        duration_days: int = 30,
        renewed_at: datetime | None = None,
    ) -> TrialSubscription:
        current = renewed_at or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("renewed_at must be timezone-aware")

        if duration_days <= 0:
            raise ValueError("duration_days must be positive")

        if self.subscription is None:
            raise RuntimeError("subscription has not been initialized")

        start = max(current, self.subscription.expires_at)

        self.subscription = TrialSubscription(
            organization_id=self.organization_id,
            deployment_id=self.deployment_id,
            started_at=start,
            expires_at=start + timedelta(days=duration_days),
            state=TrialSubscriptionState.ACTIVE,
            edition=self.subscription.edition,
        )

        self._persist()
        return self.subscription

    def suspend(self) -> TrialSubscription:
        if self.subscription is None:
            raise RuntimeError("trial or subscription has not been initialized")

        current = self.subscription

        self.subscription = TrialSubscription(
            organization_id=current.organization_id,
            deployment_id=current.deployment_id,
            started_at=current.started_at,
            expires_at=current.expires_at,
            state=TrialSubscriptionState.SUSPENDED,
            edition=current.edition,
        )

        self._persist()
        return self.subscription

    def can_run_yoma(
        self,
        *,
        now: datetime | None = None,
    ) -> bool:
        current = self.refresh(now=now)

        return current.state in (
            TrialSubscriptionState.TRIAL,
            TrialSubscriptionState.ACTIVE,
        )

    def notification(
        self,
        *,
        now: datetime | None = None,
    ) -> str | None:
        current = self.refresh(now=now)

        if current.state is TrialSubscriptionState.EXPIRED:
            return "YOMA Trial Expired - activate your subscription to resume YOMA."

        return None

    def status(
        self,
        *,
        now: datetime | None = None,
    ) -> SubscriptionStatus:
        current = self.refresh(now=now)

        check_time = now or datetime.now(timezone.utc)

        if check_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        remaining = max(
            0,
            int((current.expires_at - check_time).total_seconds()),
        )

        active = current.state in (
            TrialSubscriptionState.TRIAL,
            TrialSubscriptionState.ACTIVE,
        )

        return SubscriptionStatus(
            organization_id=self.organization_id,
            deployment_id=self.deployment_id,
            state=current.state,
            active=active,
            trial=current.state is TrialSubscriptionState.TRIAL,
            expired=current.state is TrialSubscriptionState.EXPIRED,
            remaining_seconds=remaining,
            notification_required=current.state is TrialSubscriptionState.EXPIRED,
            executable=False,
        )

    def to_yoma_license(
        self,
        *,
        license_id: str,
        now: datetime | None = None,
    ) -> YomaLicense:
        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        subscription = self.refresh(now=current)

        if subscription.state is TrialSubscriptionState.EXPIRED:
            license_status = LicenseStatus.EXPIRED
        elif subscription.state is TrialSubscriptionState.SUSPENDED:
            license_status = LicenseStatus.SUSPENDED
        else:
            license_status = LicenseStatus.ACTIVE

        return YomaLicense(
            license_id=license_id,
            organization_id=self.organization_id,
            edition=ProductEdition(subscription.edition),
            status=license_status,
            issued_at=subscription.started_at,
            expires_at=subscription.expires_at,
            entitlements={
                "yoma": license_status is LicenseStatus.ACTIVE,
            },
        )


def create_trial_subscription_manager(
    *,
    organization_id: str,
    deployment_id: str,
    now: datetime | None = None,
    persistence: TrialSubscriptionPersistence | None = None,
) -> TrialSubscriptionManager:
    return TrialSubscriptionManager(
        organization_id=organization_id,
        deployment_id=deployment_id,
        now=now,
        persistence=persistence,
    )
