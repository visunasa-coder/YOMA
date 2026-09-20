from __future__ import annotations

from typing import Any

from yoma.office.identity import SystemIdentity, UserIdentity
from yoma.office.organization_event_bus import OrganizationEventBus
from yoma.office.organization_events import (
    OrganizationChangeEvent,
    OrganizationChangeEventStore,
)
from yoma.office.organization_event_persistence import (
    OrganizationChangeEventPersistence,
)
from yoma.office.organization_state import OrganizationStatePersistence


class CentralServerAdapter:
    """Provider-neutral adapter for an organization's central server."""

    category = "identity_registry"

    def __init__(
        self,
        name: str,
        *,
        organization_state_persistence: OrganizationStatePersistence | None = None,
        event_persistence: OrganizationChangeEventPersistence | None = None,
    ) -> None:
        if not str(name).strip():
            raise ValueError("Central server adapter name is required")

        self.name = name
        self.organization_state = organization_state_persistence
        self.event_persistence = event_persistence

        self._configured = False
        self._connected = False
        self._configuration: dict[str, Any] = {}

        self.change_events = OrganizationChangeEventStore()
        self.event_bus = OrganizationEventBus()

        self._users: dict[str, UserIdentity] = {}
        self._systems: dict[str, SystemIdentity] = {}

        self._user_state: dict[str, dict[str, Any]] = {}
        self._system_state: dict[str, dict[str, Any]] = {}

        self._user_snapshot_initialized = False
        self._system_snapshot_initialized = False

        self._restore_organization_state()

    # ------------------------------------------------------------------
    # Basic adapter state
    # ------------------------------------------------------------------

    @property
    def configured(self) -> bool:
        return self._configured

    @property
    def connected(self) -> bool:
        return self._connected

    def configure(self, configuration: dict[str, Any]) -> None:
        if not isinstance(configuration, dict):
            raise TypeError("Central server configuration must be a dictionary")

        self._configuration = dict(configuration)
        self._configured = True

    def configuration(self) -> dict[str, Any]:
        """Return non-sensitive adapter configuration."""
        sensitive_keys = {
            "api_key",
            "apikey",
            "api_secret",
            "secret",
            "password",
            "passwd",
            "token",
            "access_token",
            "refresh_token",
            "client_secret",
            "private_key",
        }

        return {
            key: value
            for key, value in self._configuration.items()
            if str(key).lower() not in sensitive_keys
        }

    def connect(self) -> bool:
        if not self._configured:
            return False

        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> dict[str, Any]:
        if not self._configured:
            return {"status": "unconfigured"}

        if not self._connected:
            return {"status": "disconnected"}

        return {"status": "connected"}

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize_user(
        self,
        record: dict[str, Any] | UserIdentity,
    ) -> UserIdentity:
        if isinstance(record, UserIdentity):
            return record

        if not isinstance(record, dict):
            raise TypeError("User record must be a dictionary")

        external_id = record.get("id", record.get("user_id"))

        if not str(external_id or "").strip():
            raise ValueError("User record requires an external id")

        return UserIdentity(
            user_id=str(external_id),
            name=record.get("name"),
            username=record.get("username"),
            email=record.get("email"),
            department=record.get("department"),
            role=record.get("role"),
            system_id=record.get("system_id"),
            active=bool(record.get("active", True)),
        )

    def normalize_system(
        self,
        record: dict[str, Any] | SystemIdentity,
    ) -> SystemIdentity:
        if isinstance(record, SystemIdentity):
            return record

        if not isinstance(record, dict):
            raise TypeError("System record must be a dictionary")

        external_id = record.get("id", record.get("system_id"))

        if not str(external_id or "").strip():
            raise ValueError("System record requires an external id")

        return SystemIdentity(
            system_id=str(external_id),
            name=record.get("name"),
            system_number=record.get("system_number"),
            active=bool(record.get("active", True)),
        )

    _normalize_user = normalize_user
    _normalize_system = normalize_system

    # ------------------------------------------------------------------
    # Simple synchronization
    # ------------------------------------------------------------------

    def sync_users(
        self,
        records: list[dict[str, Any] | UserIdentity],
    ) -> list[UserIdentity]:
        if not isinstance(records, list):
            raise TypeError("Users must be a list")

        return [self.normalize_user(record) for record in records]

    def sync_systems(
        self,
        records: list[dict[str, Any] | SystemIdentity],
    ) -> list[SystemIdentity]:
        if not isinstance(records, list):
            raise TypeError("Systems must be a list")

        return [self.normalize_system(record) for record in records]

    # ------------------------------------------------------------------
    # User/system access
    # ------------------------------------------------------------------

    def get_user(self, user_id: str) -> UserIdentity | None:
        if not str(user_id).strip():
            raise ValueError("user_id is required")

        return self._users.get(str(user_id))

    def list_users(self) -> list[UserIdentity]:
        return list(self._users.values())

    def resolve_user(self, external_id: str) -> UserIdentity | None:
        if not str(external_id).strip():
            raise ValueError("external_id is required")

        return self._users.get(str(external_id))

    def get_system(self, system_id: str) -> SystemIdentity | None:
        if not str(system_id).strip():
            raise ValueError("system_id is required")

        return self._systems.get(str(system_id))

    def list_systems(self) -> list[SystemIdentity]:
        return list(self._systems.values())

    # ------------------------------------------------------------------
    # State conversion
    # ------------------------------------------------------------------

    def _user_state_from_identity(
        self,
        user: UserIdentity,
    ) -> dict[str, Any]:
        return {
            "user_id": user.user_id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "department": user.department,
            "role": user.role,
            "system_id": user.system_id,
            "active": user.active,
        }

    def _system_state_from_identity(
        self,
        system: SystemIdentity,
    ) -> dict[str, Any]:
        return {
            "system_id": system.system_id,
            "name": system.name,
            "system_number": system.system_number,
            "active": system.active,
        }

    # ------------------------------------------------------------------
    # Organization-state persistence
    # ------------------------------------------------------------------

    def _restore_organization_state(self) -> None:
        if self.organization_state is None:
            return

        users = self.organization_state.users()
        systems = self.organization_state.systems()

        self._users = {
            user.user_id: user
            for user in users
        }

        self._systems = {
            system.system_id: system
            for system in systems
        }

        self._user_state = {
            user.user_id: self._user_state_from_identity(user)
            for user in users
        }

        self._system_state = {
            system.system_id: self._system_state_from_identity(system)
            for system in systems
        }

        self._user_snapshot_initialized = bool(users)
        self._system_snapshot_initialized = bool(systems)

    def _persist_users(self) -> None:
        if self.organization_state is not None:
            self.organization_state.save_users(
                list(self._users.values())
            )

    def _persist_systems(self) -> None:
        if self.organization_state is not None:
            self.organization_state.save_systems(
                list(self._systems.values())
            )

    # ------------------------------------------------------------------
    # Change events
    # ------------------------------------------------------------------

    def _emit_change_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        previous_state: dict[str, Any] | None = None,
        current_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrganizationChangeEvent:
        event = OrganizationChangeEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_state=previous_state,
            current_state=current_state,
            metadata=metadata or {},
        )

        self.change_events.add(event)

        if self.event_persistence is not None:
            self.event_persistence.save(event)

        self.event_bus.publish(event)

        return event

    # ------------------------------------------------------------------
    # User reconciliation
    # ------------------------------------------------------------------

    def reconcile_users(
        self,
        records: list[dict[str, Any] | UserIdentity],
    ) -> dict[str, Any]:
        if not isinstance(records, list):
            raise TypeError("Users must be a list")

        # Normalize the entire collection before changing state.
        normalized = [
            self.normalize_user(record)
            for record in records
        ]

        incoming = {
            user.user_id: user
            for user in normalized
        }

        previous = dict(self._user_state)
        initial = not self._user_snapshot_initialized

        added: list[str] = []
        removed: list[str] = []
        updated: list[str] = []
        unchanged: list[str] = []

        # Deterministic processing order.
        for user in sorted(normalized, key=lambda item: item.user_id):
            user_id = user.user_id
            current_state = self._user_state_from_identity(user)
            previous_state = previous.get(user_id)

            if previous_state is None:
                added.append(user_id)

                self._emit_change_event(
                    event_type="USER_ADDED",
                    entity_type="user",
                    entity_id=user_id,
                    current_state=current_state,
                )
                continue

            if previous_state == current_state:
                unchanged.append(user_id)
                continue

            updated.append(user_id)

            if (
                previous_state.get("active") is False
                and current_state.get("active") is True
            ):
                event_type = "USER_ACTIVATED"
            elif (
                previous_state.get("active") is True
                and current_state.get("active") is False
            ):
                event_type = "USER_DEACTIVATED"
            else:
                event_type = "USER_UPDATED"

            self._emit_change_event(
                event_type=event_type,
                entity_type="user",
                entity_id=user_id,
                previous_state=previous_state,
                current_state=current_state,
            )

        for user_id in sorted(previous):
            if user_id not in incoming:
                removed.append(user_id)

                self._emit_change_event(
                    event_type="USER_REMOVED",
                    entity_type="user",
                    entity_id=user_id,
                    previous_state=previous[user_id],
                )

        self._users = incoming

        self._user_state = {
            user.user_id: self._user_state_from_identity(user)
            for user in normalized
        }

        self._user_snapshot_initialized = True
        self._persist_users()

        return {
            "initial": initial,
            "added": added,
            "removed": removed,
            "updated": updated,
            "unchanged": unchanged,
        }

    # ------------------------------------------------------------------
    # System reconciliation
    # ------------------------------------------------------------------

    def reconcile_systems(
        self,
        records: list[dict[str, Any] | SystemIdentity],
    ) -> dict[str, Any]:
        if not isinstance(records, list):
            raise TypeError("Systems must be a list")

        # Normalize the entire collection before changing state.
        normalized = [
            self.normalize_system(record)
            for record in records
        ]

        incoming = {
            system.system_id: system
            for system in normalized
        }

        previous = dict(self._system_state)
        initial = not self._system_snapshot_initialized

        added: list[str] = []
        removed: list[str] = []
        updated: list[str] = []
        unchanged: list[str] = []

        # Deterministic processing order.
        for system in sorted(normalized, key=lambda item: item.system_id):
            system_id = system.system_id
            current_state = self._system_state_from_identity(system)
            previous_state = previous.get(system_id)

            if previous_state is None:
                added.append(system_id)

                self._emit_change_event(
                    event_type="SYSTEM_ADDED",
                    entity_type="system",
                    entity_id=system_id,
                    current_state=current_state,
                )
                continue

            if previous_state == current_state:
                unchanged.append(system_id)
                continue

            updated.append(system_id)

            if (
                previous_state.get("active") is False
                and current_state.get("active") is True
            ):
                event_type = "SYSTEM_ACTIVATED"
            elif (
                previous_state.get("active") is True
                and current_state.get("active") is False
            ):
                event_type = "SYSTEM_DEACTIVATED"
            else:
                event_type = "SYSTEM_UPDATED"

            self._emit_change_event(
                event_type=event_type,
                entity_type="system",
                entity_id=system_id,
                previous_state=previous_state,
                current_state=current_state,
            )

        for system_id in sorted(previous):
            if system_id not in incoming:
                removed.append(system_id)

                self._emit_change_event(
                    event_type="SYSTEM_REMOVED",
                    entity_type="system",
                    entity_id=system_id,
                    previous_state=previous[system_id],
                )

        self._systems = incoming

        self._system_state = {
            system.system_id: self._system_state_from_identity(system)
            for system in normalized
        }

        self._system_snapshot_initialized = True
        self._persist_systems()

        return {
            "initial": initial,
            "added": added,
            "removed": removed,
            "updated": updated,
            "unchanged": unchanged,
        }

    # ------------------------------------------------------------------
    # Event access
    # ------------------------------------------------------------------

    def events(self) -> list[OrganizationChangeEvent]:
        return self.change_events.events()

    def event_count(self) -> int:
        return self.change_events.count()

    # ------------------------------------------------------------------
    # Persistent event replay
    # ------------------------------------------------------------------

    def replay_events(self) -> int:
        """Replay persisted organization events through the existing event bus."""
        if self.event_persistence is None:
            return 0

        return self.event_persistence.replay(self.event_bus)