"""Persistent licensing state for YOMA."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .activation import ActivationStatus


@dataclass(frozen=True)
class PersistedActivation:
    """Immutable persisted activation state."""

    license_id: str
    organization_id: str
    status: ActivationStatus
    activated_at: str | None


class LicensePersistence:
    """Persist and recover activation state safely."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def save(self, state: PersistedActivation) -> None:
        """Atomically persist activation state."""

        if not isinstance(state, PersistedActivation):
            raise TypeError("state must be a PersistedActivation")

        self._path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "license_id": state.license_id,
            "organization_id": state.organization_id,
            "status": state.status.value,
            "activated_at": state.activated_at,
        }

        temporary = self._path.with_suffix(
            self._path.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

        temporary.replace(self._path)

    def load(self) -> PersistedActivation | None:
        """Load persisted activation state.

        Missing or malformed state is treated as unavailable rather
        than silently becoming active.
        """

        if not self._path.exists():
            return None

        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )

            if not isinstance(payload, dict):
                return None

            license_id = payload.get("license_id")
            organization_id = payload.get("organization_id")
            status_value = payload.get("status")
            activated_at = payload.get("activated_at")

            if not isinstance(license_id, str):
                return None

            if not isinstance(organization_id, str):
                return None

            if not isinstance(status_value, str):
                return None

            if activated_at is not None and not isinstance(
                activated_at, str
            ):
                return None

            status = ActivationStatus(status_value)

            return PersistedActivation(
                license_id=license_id,
                organization_id=organization_id,
                status=status,
                activated_at=activated_at,
            )

        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
        ):
            return None

    def clear(self) -> None:
        """Remove persisted activation state safely."""

        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
