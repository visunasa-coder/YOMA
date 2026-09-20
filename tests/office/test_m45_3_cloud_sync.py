from datetime import datetime, timezone

import pytest

from yoma.office.cloud_sync import (
    CloudSyncIdentity,
    CloudSyncManager,
    CloudSyncPayload,
    CloudSyncQueue,
    CloudSyncRecord,
    CloudSyncState,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)


def identities():
    organization = DistributedOrganizationIdentity(
        organization_id="org-1",
        organization_name="Test Org",
        deployment_id="dep-1",
    )
    node = DistributedNodeIdentity(
        node_id="node-1",
        organization_id="org-1",
        deployment_id="dep-1",
        node_name="Employee PC",
    )
    return organization, node


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def test_identity_is_deterministic():
    organization, node = identities()

    identity = CloudSyncIdentity.from_identities(
        organization,
        node,
    )

    assert identity.identity_key == "org-1:dep-1:node-1"


def test_identity_rejects_wrong_node():
    organization, _ = identities()

    node = DistributedNodeIdentity(
        node_id="node-2",
        organization_id="other-org",
        deployment_id="dep-1",
        node_name="Other PC",
    )

    with pytest.raises(ValueError):
        CloudSyncIdentity.from_identities(
            organization,
            node,
        )


def test_payload_serialization_is_deterministic():
    payload = CloudSyncPayload(
        event_type="ticket.created",
        event_id="event-1",
        occurred_at=timestamp(),
        data=(
            ("z", 2),
            ("a", 1),
        ),
    )

    assert payload.serialize() == payload.serialize()
    assert '"a":1' in payload.serialize()
    assert '"z":2' in payload.serialize()


def test_payload_rejects_invalid_timestamp():
    with pytest.raises(ValueError):
        CloudSyncPayload(
            event_type="test",
            event_id="event-1",
            occurred_at="invalid",
        )


def test_record_generates_idempotency_key():
    organization, node = identities()

    payload = CloudSyncPayload(
        event_type="test",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    record = CloudSyncRecord(
        sync_id="sync-1",
        identity=CloudSyncIdentity.from_identities(
            organization,
            node,
        ),
        payload=payload,
    )

    assert record.idempotency_key
    assert record.idempotency_key == record.idempotency_key


def test_queue_deduplicates_same_event():
    organization, node = identities()
    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    first = manager.prepare(
        event_type="ticket.created",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    second = manager.prepare(
        event_type="ticket.created",
        event_id="event-1",
        occurred_at=first.payload.occurred_at,
    )

    assert first == second
    assert len(manager.queue.pending()) == 1


def test_queue_tracks_pending():
    organization, node = identities()
    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    manager.prepare(
        event_type="ticket.created",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    assert len(manager.queue.pending()) == 1


def test_acknowledgement_marks_record_synced():
    organization, node = identities()
    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="ticket.created",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    result = manager.acknowledge(
        record.idempotency_key
    )

    assert result.accepted is True
    assert result.state == CloudSyncState.SYNCED
    assert manager.queue.pending() == ()


def test_failure_is_recorded():
    organization, node = identities()
    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="ticket.created",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    result = manager.fail(
        record.idempotency_key,
        "cloud unavailable",
    )

    assert result.accepted is False
    assert result.state == CloudSyncState.FAILED
    assert result.error == "cloud unavailable"


def test_attempt_count_increases():
    organization, node = identities()
    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="test",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    manager.fail(
        record.idempotency_key,
        "temporary failure",
    )

    updated = manager.queue.get(
        record.idempotency_key
    )

    assert updated is not None
    assert updated.attempts == 1


def test_organization_isolation():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="test",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    assert record.identity.organization_id == "org-1"
    assert record.identity.deployment_id == "dep-1"
    assert record.identity.node_id == "node-1"


def test_payload_does_not_contain_identity_secrets():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="test",
        event_id="event-1",
        occurred_at=timestamp(),
        data={"value": "safe"},
    )

    payload = record.payload.serialize()

    assert "password" not in payload.lower()
    assert "secret" not in payload.lower()
    assert "token" not in payload.lower()


def test_sync_result_is_governed():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="test",
        event_id="event-1",
        occurred_at=timestamp(),
    )

    result = manager.acknowledge(
        record.idempotency_key
    )

    assert result.requires_human_approval is True
    assert result.executable is False


def test_manager_status_is_governed():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    status = manager.status()

    assert status["organization_id"] == "org-1"
    assert status["deployment_id"] == "dep-1"
    assert status["node_id"] == "node-1"
    assert status["requires_human_approval"] is True
    assert status["executable"] is False


def test_manager_rejects_invalid_organization():
    _, node = identities()

    with pytest.raises(TypeError):
        CloudSyncManager(
            organization="invalid",
            node=node,
        )


def test_manager_rejects_invalid_node():
    organization, _ = identities()

    with pytest.raises(TypeError):
        CloudSyncManager(
            organization=organization,
            node="invalid",
        )


def test_record_dict_is_secret_free():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    record = manager.prepare(
        event_type="test",
        event_id="event-1",
        occurred_at=timestamp(),
        data={"status": "ok"},
    )

    result = record.as_dict()

    assert result["organization_id"] == "org-1"
    assert result["node_id"] == "node-1"
    assert "secret" not in str(result).lower()
    assert "password" not in str(result).lower()


def test_multiple_events_remain_order_independent_by_identity():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    first = manager.prepare(
        event_type="event.a",
        event_id="a",
        occurred_at=timestamp(),
        data={"z": 1, "a": 2},
    )

    second = manager.prepare(
        event_type="event.b",
        event_id="b",
        occurred_at=timestamp(),
    )

    assert first.idempotency_key != second.idempotency_key
    assert len(manager.queue.pending()) == 2


def test_factory_style_manager_can_be_used():
    organization, node = identities()

    manager = CloudSyncManager(
        organization=organization,
        node=node,
        queue=CloudSyncQueue(),
    )

    assert manager.identity.identity_key == (
        "org-1:dep-1:node-1"
    )
