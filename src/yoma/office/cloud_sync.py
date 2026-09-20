from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)


class CloudSyncState(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass(frozen=True)
class CloudSyncIdentity:
    organization_id: str
    deployment_id: str
    node_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "organization_id",
            "deployment_id",
            "node_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

    @property
    def identity_key(self) -> str:
        return (
            f"{self.organization_id}:"
            f"{self.deployment_id}:"
            f"{self.node_id}"
        )

    @classmethod
    def from_identities(
        cls,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
    ) -> "CloudSyncIdentity":
        if not node.belongs_to(organization):
            raise ValueError(
                "node does not belong to the organization deployment"
            )

        return cls(
            organization_id=organization.organization_id,
            deployment_id=organization.deployment_id,
            node_id=node.node_id,
        )


@dataclass(frozen=True)
class CloudSyncPayload:
    event_type: str
    event_id: str
    occurred_at: str
    data: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "event_type",
            "event_id",
            "occurred_at",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        try:
            datetime.fromisoformat(
                self.occurred_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                "occurred_at must be a valid ISO timestamp"
            ) from exc

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "data": {
                key: value
                for key, value in self.data
            },
        }

    def serialize(self) -> str:
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )


@dataclass(frozen=True)
class CloudSyncRecord:
    sync_id: str
    identity: CloudSyncIdentity
    payload: CloudSyncPayload
    state: CloudSyncState = CloudSyncState.PENDING
    attempts: int = 0
    last_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sync_id, str) or not self.sync_id.strip():
            raise ValueError("sync_id must be a non-empty string")

        if self.attempts < 0:
            raise ValueError("attempts cannot be negative")

        if self.last_error is not None and not isinstance(
            self.last_error, str
        ):
            raise TypeError("last_error must be a string or None")

    @property
    def idempotency_key(self) -> str:
        raw = (
            f"{self.identity.identity_key}:"
            f"{self.payload.event_id}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "organization_id": self.identity.organization_id,
            "deployment_id": self.identity.deployment_id,
            "node_id": self.identity.node_id,
            "payload": self.payload.as_dict(),
            "state": self.state.value,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "idempotency_key": self.idempotency_key,
        }


@dataclass(frozen=True)
class CloudSyncResult:
    sync_id: str
    state: CloudSyncState
    accepted: bool
    duplicate: bool = False
    error: str | None = None
    requires_human_approval: bool = True
    executable: bool = False


class CloudSyncQueue:
    """In-memory outbound queue with deterministic deduplication."""

    def __init__(self) -> None:
        self._records: dict[str, CloudSyncRecord] = {}

    def enqueue(self, record: CloudSyncRecord) -> CloudSyncRecord:
        key = record.idempotency_key

        existing = self._records.get(key)
        if existing is not None:
            return existing

        self._records[key] = record
        return record

    def get(self, idempotency_key: str) -> CloudSyncRecord | None:
        return self._records.get(idempotency_key)

    def pending(self) -> tuple[CloudSyncRecord, ...]:
        return tuple(
            record
            for record in self._records.values()
            if record.state == CloudSyncState.PENDING
        )

    def mark_synced(self, idempotency_key: str) -> CloudSyncRecord:
        record = self._records[idempotency_key]

        updated = CloudSyncRecord(
            sync_id=record.sync_id,
            identity=record.identity,
            payload=record.payload,
            state=CloudSyncState.SYNCED,
            attempts=record.attempts + 1,
            last_error=None,
        )

        self._records[idempotency_key] = updated
        return updated

    def mark_failed(
        self,
        idempotency_key: str,
        error: str,
    ) -> CloudSyncRecord:
        if not isinstance(error, str) or not error.strip():
            raise ValueError("error must be a non-empty string")

        record = self._records[idempotency_key]

        updated = CloudSyncRecord(
            sync_id=record.sync_id,
            identity=record.identity,
            payload=record.payload,
            state=CloudSyncState.FAILED,
            attempts=record.attempts + 1,
            last_error=error,
        )

        self._records[idempotency_key] = updated
        return updated


class CloudSyncManager:
    """Governed cloud synchronization boundary.

    This component prepares and tracks synchronization work.
    It does not execute business actions.
    """

    def __init__(
        self,
        *,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
        queue: CloudSyncQueue | None = None,
    ) -> None:
        if not isinstance(
            organization,
            DistributedOrganizationIdentity,
        ):
            raise TypeError(
                "organization must be a "
                "DistributedOrganizationIdentity"
            )

        if not isinstance(
            node,
            DistributedNodeIdentity,
        ):
            raise TypeError(
                "node must be a DistributedNodeIdentity"
            )

        if not node.belongs_to(organization):
            raise ValueError(
                "node does not belong to the organization deployment"
            )

        self.organization = organization
        self.node = node
        self.identity = CloudSyncIdentity.from_identities(
            organization,
            node,
        )
        self.queue = queue or CloudSyncQueue()

    def prepare(
        self,
        *,
        event_type: str,
        event_id: str,
        occurred_at: str,
        data: dict[str, Any] | None = None,
    ) -> CloudSyncRecord:
        payload = CloudSyncPayload(
            event_type=event_type,
            event_id=event_id,
            occurred_at=occurred_at,
            data=tuple(
                sorted((data or {}).items())
            ),
        )

        record = CloudSyncRecord(
            sync_id=hashlib.sha256(
                (
                    f"{self.identity.identity_key}:"
                    f"{event_id}"
                ).encode("utf-8")
            ).hexdigest(),
            identity=self.identity,
            payload=payload,
        )

        return self.queue.enqueue(record)

    def acknowledge(
        self,
        idempotency_key: str,
    ) -> CloudSyncResult:
        record = self.queue.mark_synced(idempotency_key)

        return CloudSyncResult(
            sync_id=record.sync_id,
            state=record.state,
            accepted=True,
        )

    def fail(
        self,
        idempotency_key: str,
        error: str,
    ) -> CloudSyncResult:
        record = self.queue.mark_failed(
            idempotency_key,
            error,
        )

        return CloudSyncResult(
            sync_id=record.sync_id,
            state=record.state,
            accepted=False,
            error=record.last_error,
        )

    def status(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization.organization_id,
            "deployment_id": self.organization.deployment_id,
            "node_id": self.node.node_id,
            "pending_count": len(self.queue.pending()),
            "requires_human_approval": True,
            "executable": False,
        }


def create_cloud_sync_manager(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
    queue: CloudSyncQueue | None = None,
) -> CloudSyncManager:
    return CloudSyncManager(
        organization=organization,
        node=node,
        queue=queue,
    )
