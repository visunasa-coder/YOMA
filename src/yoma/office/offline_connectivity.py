from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .cloud_sync import (
    CloudSyncManager,
    CloudSyncRecord,
    CloudSyncState,
)
from .distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)


class ConnectivityState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OfflineQueueStatus:
    state: ConnectivityState
    pending_count: int
    synced_count: int
    failed_count: int
    governed: bool = True
    requires_human_approval: bool = True
    executable: bool = False


@dataclass(frozen=True)
class OfflineSyncResult:
    state: ConnectivityState
    attempted: int
    synced: int
    remaining: int
    failed: int
    records: tuple[CloudSyncRecord, ...]
    governed: bool = True
    requires_human_approval: bool = True
    executable: bool = False


class OfflineConnectivityManager:
    """Local-first offline buffering and connectivity state.

    M45.5 does not perform network transport or business execution.
    It retains synchronization work locally and exposes pending work
    when connectivity returns.
    """

    def __init__(
        self,
        *,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
        sync_manager: CloudSyncManager | None = None,
    ) -> None:
        if not isinstance(
            organization,
            DistributedOrganizationIdentity,
        ):
            raise TypeError(
                "organization must be a DistributedOrganizationIdentity"
            )

        if not isinstance(node, DistributedNodeIdentity):
            raise TypeError(
                "node must be a DistributedNodeIdentity"
            )

        if not node.belongs_to(organization):
            raise ValueError(
                "node does not belong to organization deployment"
            )

        self.organization = organization
        self.node = node

        self.sync_manager = sync_manager or CloudSyncManager(
            organization=organization,
            node=node,
        )

        self._state = ConnectivityState.UNKNOWN
        self._local_records: dict[str, CloudSyncRecord] = {}

    @property
    def state(self) -> ConnectivityState:
        return self._state

    def set_online(self) -> ConnectivityState:
        self._state = ConnectivityState.ONLINE
        return self._state

    def set_offline(self) -> ConnectivityState:
        self._state = ConnectivityState.OFFLINE
        return self._state

    def set_unknown(self) -> ConnectivityState:
        self._state = ConnectivityState.UNKNOWN
        return self._state

    def queue(self, record: CloudSyncRecord) -> CloudSyncRecord:
        """Retain a synchronization record in the local offline buffer."""

        if not isinstance(record, CloudSyncRecord):
            raise TypeError(
                "record must be a CloudSyncRecord"
            )

        existing = self._local_records.get(record.sync_id)

        if existing is not None:
            return existing

        self._local_records[record.sync_id] = record
        return record

    def queue_many(
        self,
        records: tuple[CloudSyncRecord, ...] | list[CloudSyncRecord],
    ) -> tuple[CloudSyncRecord, ...]:
        queued: list[CloudSyncRecord] = []

        for record in records:
            queued.append(self.queue(record))

        return tuple(queued)

    def pending(self) -> tuple[CloudSyncRecord, ...]:
        return tuple(
            record
            for record in self._local_records.values()
            if record.state == CloudSyncState.PENDING
        )

    def records(self) -> tuple[CloudSyncRecord, ...]:
        return tuple(self._local_records.values())

    def status(self) -> OfflineQueueStatus:
        records = self.records()

        return OfflineQueueStatus(
            state=self._state,
            pending_count=sum(
                1
                for record in records
                if record.state == CloudSyncState.PENDING
            ),
            synced_count=sum(
                1
                for record in records
                if record.state == CloudSyncState.SYNCED
            ),
            failed_count=sum(
                1
                for record in records
                if record.state == CloudSyncState.FAILED
            ),
        )

    def prepare_reconnect_sync(self) -> OfflineSyncResult:
        """Expose locally buffered work after connectivity is restored.

        No network request is performed by M45.5.
        """

        pending = self.pending()

        if self._state != ConnectivityState.ONLINE:
            return OfflineSyncResult(
                state=self._state,
                attempted=0,
                synced=0,
                remaining=len(pending),
                failed=0,
                records=pending,
            )

        return OfflineSyncResult(
            state=self._state,
            attempted=len(pending),
            synced=0,
            remaining=len(pending),
            failed=0,
            records=pending,
        )

    def mark_synced(self, idempotency_key: str) -> CloudSyncRecord:
        record = self._local_records[idempotency_key]

        updated = CloudSyncRecord(
            sync_id=record.sync_id,
            identity=record.identity,
            payload=record.payload,
            state=CloudSyncState.SYNCED,
            attempts=record.attempts + 1,
            last_error=None,
        )

        self._local_records[idempotency_key] = updated
        return updated

    def mark_failed(
        self,
        idempotency_key: str,
        reason: str,
    ) -> CloudSyncRecord:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "reason must be a non-empty string"
            )

        record = self._local_records[idempotency_key]

        updated = CloudSyncRecord(
            sync_id=record.sync_id,
            identity=record.identity,
            payload=record.payload,
            state=CloudSyncState.FAILED,
            attempts=record.attempts + 1,
            last_error=reason,
        )

        self._local_records[idempotency_key] = updated
        return updated

    def clear_failed(self) -> int:
        count = 0

        for key, record in tuple(self._local_records.items()):
            if record.state == CloudSyncState.FAILED:
                updated = CloudSyncRecord(
                    sync_id=record.sync_id,
                    identity=record.identity,
                    payload=record.payload,
                    state=CloudSyncState.PENDING,
                    attempts=record.attempts,
                    last_error=None,
                )

                self._local_records[key] = updated
                count += 1

        return count

    def prepare_cloud_sync(
        self,
        *,
        event_type: str,
        event_id: str,
        occurred_at: str,
        data: dict[str, Any] | None = None,
    ) -> CloudSyncRecord:
        """Create a cloud-sync record through the M45.3 public API.

        The record is immediately retained in the local offline buffer.
        """

        record = self.sync_manager.prepare(
            event_type=event_type,
            event_id=event_id,
            occurred_at=occurred_at,
            data=data,
        )

        return self.queue(record)

    def acknowledge_cloud_sync(
        self,
        idempotency_key: str,
    ) -> CloudSyncRecord:
        """Record successful synchronization locally and in M45.3."""

        result = self.sync_manager.acknowledge(
            idempotency_key
        )

        updated = self.mark_synced(idempotency_key)

        # The M45.3 result remains the authoritative synchronization
        # boundary; M45.5 mirrors the resulting state locally.
        if hasattr(result, "record"):
            returned_record = result.record
            if isinstance(returned_record, CloudSyncRecord):
                updated = returned_record
                self._local_records[idempotency_key] = returned_record

        return updated

    def fail_cloud_sync(
        self,
        idempotency_key: str,
        reason: str,
    ) -> CloudSyncRecord:
        """Record a failed synchronization attempt."""

        result = self.sync_manager.fail(
            idempotency_key,
            reason,
        )

        updated = self.mark_failed(
            idempotency_key,
            reason,
        )

        if hasattr(result, "record"):
            returned_record = result.record
            if isinstance(returned_record, CloudSyncRecord):
                updated = returned_record
                self._local_records[idempotency_key] = returned_record

        return updated

    def factory_status(self) -> dict[str, object]:
        status = self.status()

        return {
            "organization_id": self.organization.organization_id,
            "deployment_id": self.organization.deployment_id,
            "node_id": self.node.node_id,
            "state": status.state.value,
            "pending_count": status.pending_count,
            "synced_count": status.synced_count,
            "failed_count": status.failed_count,
            "governed": status.governed,
            "requires_human_approval": (
                status.requires_human_approval
            ),
            "executable": status.executable,
        }


def create_offline_connectivity_manager(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
    sync_manager: CloudSyncManager | None = None,
) -> OfflineConnectivityManager:
    return OfflineConnectivityManager(
        organization=organization,
        node=node,
        sync_manager=sync_manager,
    )
