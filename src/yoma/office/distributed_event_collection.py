from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from yoma.office.cloud_sync import (
    CloudSyncManager,
    CloudSyncRecord,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)
from yoma.office.operations import OperationalEvent


@dataclass(frozen=True)
class DistributedEventEnvelope:
    event: OperationalEvent
    organization_id: str
    deployment_id: str
    node_id: str
    sequence: int

    def __post_init__(self) -> None:
        if not isinstance(self.event, OperationalEvent):
            raise TypeError(
                "event must be an OperationalEvent"
            )

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

        if self.sequence < 0:
            raise ValueError(
                "sequence cannot be negative"
            )

    @property
    def event_id(self) -> str:
        return self.event.event_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event.event_id,
            "event_type": self.event.event_type,
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "node_id": self.node_id,
            "sequence": self.sequence,
            "occurred_at": self.event.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class DistributedEventCollectionResult:
    organization_id: str
    deployment_id: str
    node_id: str
    received_count: int
    accepted_count: int
    duplicate_count: int
    rejected_count: int
    envelopes: tuple[DistributedEventEnvelope, ...] = ()
    sync_records: tuple[CloudSyncRecord, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False


class DistributedEventCollector:
    """Collects existing YOMA OperationalEvents for distributed sync.

    This component does not replace the canonical OperationalEventBus,
    execute business actions, or authorize actions.
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
        self.sync_manager = sync_manager or CloudSyncManager(
            organization=organization,
            node=node,
        )

        self._seen_event_ids: set[str] = set()
        self._sequence = 0

    def collect(
        self,
        events: list[OperationalEvent] | tuple[OperationalEvent, ...],
    ) -> DistributedEventCollectionResult:
        if not isinstance(events, (list, tuple)):
            raise TypeError(
                "events must be a list or tuple"
            )

        envelopes: list[DistributedEventEnvelope] = []
        sync_records: list[CloudSyncRecord] = []

        duplicate_count = 0
        rejected_count = 0

        # Validate event types BEFORE sorting.
        valid_events: list[OperationalEvent] = []

        for event in events:
            if not isinstance(event, OperationalEvent):
                rejected_count += 1
                continue

            if event.organization_id != self.organization.organization_id:
                rejected_count += 1
                continue

            valid_events.append(event)

        ordered_events = sorted(
            valid_events,
            key=lambda event: (
                event.occurred_at,
                event.event_id,
            ),
        )

        for event in ordered_events:
            if event.event_id in self._seen_event_ids:
                duplicate_count += 1
                continue

            envelope = DistributedEventEnvelope(
                event=event,
                organization_id=self.organization.organization_id,
                deployment_id=self.organization.deployment_id,
                node_id=self.node.node_id,
                sequence=self._sequence,
            )

            self._sequence += 1
            self._seen_event_ids.add(event.event_id)
            envelopes.append(envelope)

            record = self.sync_manager.prepare(
                event_type=event.event_type,
                event_id=event.event_id,
                occurred_at=event.occurred_at.isoformat(),
                data=dict(event.data),
            )

            sync_records.append(record)

        return DistributedEventCollectionResult(
            organization_id=self.organization.organization_id,
            deployment_id=self.organization.deployment_id,
            node_id=self.node.node_id,
            received_count=len(events),
            accepted_count=len(envelopes),
            duplicate_count=duplicate_count,
            rejected_count=rejected_count,
            envelopes=tuple(envelopes),
            sync_records=tuple(sync_records),
        )

    def reset_seen_events(self) -> None:
        self._seen_event_ids.clear()

    @property
    def sequence(self) -> int:
        return self._sequence

    def status(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization.organization_id,
            "deployment_id": self.organization.deployment_id,
            "node_id": self.node.node_id,
            "seen_event_count": len(self._seen_event_ids),
            "sequence": self._sequence,
            "requires_human_approval": True,
            "executable": False,
        }


def create_distributed_event_collector(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
    sync_manager: CloudSyncManager | None = None,
) -> DistributedEventCollector:
    return DistributedEventCollector(
        organization=organization,
        node=node,
        sync_manager=sync_manager,
    )
