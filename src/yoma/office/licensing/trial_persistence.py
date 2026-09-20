"""Persistent trial and subscription state for YOMA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .trial_subscription import TrialSubscription


class TrialSubscriptionPersistence:
    """Persist trial/subscription lifecycle state safely."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def save(self, subscription: TrialSubscription) -> None:
        from .trial_subscription import TrialSubscription

        if not isinstance(subscription, TrialSubscription):
            raise TypeError("subscription must be a TrialSubscription")

        self._path.parent.mkdir(parents=True, exist_ok=True)

        payload = subscription.as_dict()

        temporary = self._path.with_suffix(
            self._path.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

        temporary.replace(self._path)

    def load(self) -> TrialSubscription | None:
        if not self._path.exists():
            return None

        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )

            if not isinstance(payload, dict):
                return None

            organization_id = payload.get("organization_id")
            deployment_id = payload.get("deployment_id")
            started_at = payload.get("started_at")
            expires_at = payload.get("expires_at")
            state = payload.get("state")
            edition = payload.get("edition")

            if not all(
                isinstance(value, str)
                for value in (
                    organization_id,
                    deployment_id,
                    started_at,
                    expires_at,
                    state,
                    edition,
                )
            ):
                return None

            from datetime import datetime

            from .trial_subscription import TrialSubscriptionState
            from .trial_subscription import TrialSubscription

            return TrialSubscription(
                organization_id=organization_id,
                deployment_id=deployment_id,
                started_at=datetime.fromisoformat(started_at),
                expires_at=datetime.fromisoformat(expires_at),
                state=TrialSubscriptionState(state),
                edition=edition,
            )

        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
        ):
            return None

    def clear(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
