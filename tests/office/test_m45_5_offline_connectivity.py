from datetime import datetime, timezone

import pytest

from yoma.office.cloud_sync import (
    CloudSyncIdentity,
    CloudSyncManager,
    CloudSyncPayload,
    CloudSyncRecord,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)
from yoma.office.offline_connectivity import (
    ConnectivityState,
    OfflineConnectivityManager,
)


def make_identity():
    organization = DistributedOrganizationIdentity(
        organization_id="org-1",
        organization_name="Test Organization",
        deployment_id="dep-1",
    )

    node = DistributedNodeIdentity(
        node_id="node-1",
        organization_id="org-1",
        deployment_id="dep-1",
        node_name="Employee PC",
    )

    return organization, node


def make_manager():
    organization, node = make_identity()

    return OfflineConnectivityManager(
        organization=organization,
        node=node,
    )


def make_record(event_id: str = "evt-1") -> CloudSyncRecord:
    identity = CloudSyncIdentity(
        organization_id="org-1",
        deployment_id="dep-1",
        node_id="node-1",
    )

    payload = CloudSyncPayload(
        event_type="task.updated",
        event_id=event_id,
        occurred_at="2026-09-06T12:00:00+00:00",
        data=(("task_id", "task-1"),),
    )

    return CloudSyncRecord(
        sync_id=f"sync-{event_id}",
        identity=identity,
        payload=payload,
    )


def test_initial_state_is_unknown():
    manager = make_manager()
    assert manager.state == ConnectivityState.UNKNOWN


def test_can_set_offline():
    manager = make_manager()

    assert manager.set_offline() == ConnectivityState.OFFLINE
    assert manager.state == ConnectivityState.OFFLINE


def test_can_set_online():
    manager = make_manager()

    manager.set_offline()

    assert manager.set_online() == ConnectivityState.ONLINE


def test_can_set_unknown():
    manager = make_manager()

    manager.set_online()

    assert manager.set_unknown() == ConnectivityState.UNKNOWN


def test_event_can_be_queued_while_offline():
    manager = make_manager()
    manager.set_offline()

    record = manager.queue(make_record())

    assert record in manager.pending()
    assert manager.status().pending_count == 1


def test_multiple_events_are_queued():
    manager = make_manager()
    manager.set_offline()

    records = (
        make_record("evt-1"),
        make_record("evt-2"),
        make_record("evt-3"),
    )

    queued = manager.queue_many(records)

    assert len(queued) == 3
    assert len(manager.pending()) == 3


def test_duplicate_records_are_not_added_twice():
    manager = make_manager()
    manager.set_offline()

    record = make_record()

    manager.queue(record)
    manager.queue(record)

    assert len(manager.pending()) == 1


def test_offline_reconnect_prepare_does_not_attempt_sync():
    manager = make_manager()
    manager.set_offline()
    manager.queue(make_record())

    result = manager.prepare_reconnect_sync()

    assert result.state == ConnectivityState.OFFLINE
    assert result.attempted == 0
    assert result.synced == 0
    assert result.remaining == 1


def test_online_reconnect_exposes_pending_work():
    manager = make_manager()
    manager.set_offline()
    manager.queue(make_record())
    manager.set_online()

    result = manager.prepare_reconnect_sync()

    assert result.state == ConnectivityState.ONLINE
    assert result.attempted == 1
    assert result.synced == 0
    assert result.remaining == 1


def test_mark_synced_removes_record_from_pending():
    manager = make_manager()
    record = manager.queue(make_record())

    manager.mark_synced(record.sync_id)

    assert manager.status().pending_count == 0
    assert manager.status().synced_count == 1


def test_failed_sync_is_visible():
    manager = make_manager()
    record = manager.queue(make_record())

    manager.mark_failed(
        record.sync_id,
        "network unavailable",
    )

    assert manager.status().failed_count == 1
    assert manager.status().pending_count == 0


def test_failed_records_can_be_requeued():
    manager = make_manager()
    record = manager.queue(make_record())

    manager.mark_failed(
        record.sync_id,
        "temporary failure",
    )

    assert manager.clear_failed() == 1
    assert manager.status().pending_count == 1


def test_status_is_governed():
    manager = make_manager()

    status = manager.status()

    assert status.governed is True
    assert status.requires_human_approval is True
    assert status.executable is False


def test_reconnect_result_is_non_executable():
    manager = make_manager()

    manager.queue(make_record())
    manager.set_online()

    result = manager.prepare_reconnect_sync()

    assert result.governed is True
    assert result.requires_human_approval is True
    assert result.executable is False


def test_factory_status_is_serializable():
    manager = make_manager()

    manager.set_offline()
    manager.queue(make_record())

    status = manager.factory_status()

    assert status["state"] == "offline"
    assert status["pending_count"] == 1
    assert status["executable"] is False


def test_invalid_record_is_rejected():
    manager = make_manager()

    with pytest.raises(TypeError):
        manager.queue("not-a-record")  # type: ignore[arg-type]


def test_unknown_state_does_not_sync():
    manager = make_manager()

    manager.queue(make_record())

    result = manager.prepare_reconnect_sync()

    assert result.state == ConnectivityState.UNKNOWN
    assert result.attempted == 0
    assert result.remaining == 1


def test_online_empty_queue_is_safe():
    manager = make_manager()

    manager.set_online()

    result = manager.prepare_reconnect_sync()

    assert result.attempted == 0
    assert result.remaining == 0
    assert result.synced == 0
    assert result.failed == 0


def test_pending_records_remain_after_reconnect_preparation():
    manager = make_manager()

    record = manager.queue(make_record())
    manager.set_online()

    manager.prepare_reconnect_sync()

    assert record in manager.pending()


def test_sync_manager_can_be_injected():
    organization, node = make_identity()

    sync_manager = CloudSyncManager(
        organization=organization,
        node=node,
    )

    manager = OfflineConnectivityManager(
        organization=organization,
        node=node,
        sync_manager=sync_manager,
    )

    record = make_record()

    manager.queue(record)

    assert manager.pending() == (record,)


def test_connectivity_transitions_are_deterministic():
    manager = make_manager()

    assert manager.set_offline() == ConnectivityState.OFFLINE
    assert manager.set_online() == ConnectivityState.ONLINE
    assert manager.set_unknown() == ConnectivityState.UNKNOWN
    assert manager.set_offline() == ConnectivityState.OFFLINE


def test_rejects_node_from_different_deployment():
    organization = DistributedOrganizationIdentity(
        organization_id="org-1",
        organization_name="Test Organization",
        deployment_id="dep-1",
    )

    node = DistributedNodeIdentity(
        node_id="node-1",
        organization_id="org-1",
        deployment_id="dep-2",
        node_name="Wrong Node",
    )

    with pytest.raises(ValueError):
        OfflineConnectivityManager(
            organization=organization,
            node=node,
        )


def test_factory_preserves_identity():
    organization, node = make_identity()

    manager = OfflineConnectivityManager(
        organization=organization,
        node=node,
    )

    status = manager.factory_status()

    assert status["organization_id"] == "org-1"
    assert status["deployment_id"] == "dep-1"
    assert status["node_id"] == "node-1"
