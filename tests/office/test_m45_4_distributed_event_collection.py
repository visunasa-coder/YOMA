from datetime import datetime, timedelta, timezone

import pytest

from yoma.office.distributed_event_collection import (
    DistributedEventCollector,
    DistributedEventEnvelope,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)
from yoma.office.operations import OperationalEvent


def make_identities():
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


def make_event(
    event_id: str,
    *,
    organization_id: str = "org-1",
    occurred_at=None,
):
    return OperationalEvent(
        event_id=event_id,
        event_type="ticket.created",
        occurred_at=occurred_at
        or datetime.now(timezone.utc),
        organization_id=organization_id,
        user_id="emp-1",
        source="test",
        severity="normal",
        data={"status": "open"},
    )


def test_collector_accepts_valid_identity():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    assert collector.status()["organization_id"] == "org-1"
    assert collector.status()["node_id"] == "node-1"


def test_collector_rejects_invalid_organization():
    _, node = make_identities()

    with pytest.raises(TypeError):
        DistributedEventCollector(
            organization="invalid",
            node=node,
        )


def test_collector_rejects_invalid_node():
    organization, _ = make_identities()

    with pytest.raises(TypeError):
        DistributedEventCollector(
            organization=organization,
            node="invalid",
        )


def test_collector_rejects_cross_organization_node():
    organization, _ = make_identities()

    node = DistributedNodeIdentity(
        node_id="node-2",
        organization_id="other-org",
        deployment_id="dep-1",
        node_name="Other PC",
    )

    with pytest.raises(ValueError):
        DistributedEventCollector(
            organization=organization,
            node=node,
        )


def test_collects_operational_event():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    assert result.received_count == 1
    assert result.accepted_count == 1
    assert result.duplicate_count == 0
    assert result.rejected_count == 0
    assert result.envelopes[0].event_id == "evt-1"


def test_envelope_contains_node_identity():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    envelope = result.envelopes[0]

    assert envelope.organization_id == "org-1"
    assert envelope.deployment_id == "dep-1"
    assert envelope.node_id == "node-1"


def test_duplicate_event_is_not_collected_twice():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    event = make_event("evt-1")

    first = collector.collect([event])
    second = collector.collect([event])

    assert first.accepted_count == 1
    assert second.accepted_count == 0
    assert second.duplicate_count == 1


def test_cross_organization_event_is_rejected():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event(
            "evt-foreign",
            organization_id="other-org",
        )
    ])

    assert result.accepted_count == 0
    assert result.rejected_count == 1


def test_events_are_ordered_deterministically():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    base = datetime.now(timezone.utc)

    events = [
        make_event(
            "evt-2",
            occurred_at=base + timedelta(seconds=20),
        ),
        make_event(
            "evt-1",
            occurred_at=base + timedelta(seconds=10),
        ),
    ]

    result = collector.collect(events)

    assert [
        envelope.event_id
        for envelope in result.envelopes
    ] == ["evt-1", "evt-2"]


def test_sequence_is_monotonic():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1"),
        make_event("evt-2"),
        make_event("evt-3"),
    ])

    assert [
        envelope.sequence
        for envelope in result.envelopes
    ] == [0, 1, 2]

    assert collector.sequence == 3


def test_events_become_cloud_sync_records():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    assert len(result.sync_records) == 1
    assert result.sync_records[0].payload.event_id == "evt-1"


def test_sync_record_preserves_event_type():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    assert (
        result.sync_records[0].payload.event_type
        == "ticket.created"
    )


def test_sync_record_preserves_event_data():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    data = dict(
        result.sync_records[0].payload.data
    )

    assert data["status"] == "open"


def test_empty_collection_is_safe():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([])

    assert result.received_count == 0
    assert result.accepted_count == 0
    assert result.envelopes == ()
    assert result.sync_records == ()


def test_invalid_event_is_rejected():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        "invalid-event"
    ])

    assert result.rejected_count == 1
    assert result.accepted_count == 0


def test_mixed_valid_duplicate_and_foreign_events():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    valid = make_event("evt-1")
    foreign = make_event(
        "evt-foreign",
        organization_id="other-org",
    )

    collector.collect([valid])

    result = collector.collect([
        valid,
        foreign,
        make_event("evt-2"),
    ])

    assert result.accepted_count == 1
    assert result.duplicate_count == 1
    assert result.rejected_count == 1


def test_reset_allows_event_to_be_collected_again():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    event = make_event("evt-1")

    collector.collect([event])
    collector.reset_seen_events()

    result = collector.collect([event])

    assert result.accepted_count == 1
    assert result.duplicate_count == 0


def test_result_is_governed():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    assert result.requires_human_approval is True
    assert result.executable is False


def test_envelope_is_immutable():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    result = collector.collect([
        make_event("evt-1")
    ])

    envelope = result.envelopes[0]

    with pytest.raises(Exception):
        envelope.sequence = 99


def test_status_tracks_seen_events():
    organization, node = make_identities()

    collector = DistributedEventCollector(
        organization=organization,
        node=node,
    )

    collector.collect([
        make_event("evt-1"),
        make_event("evt-2"),
    ])

    status = collector.status()

    assert status["seen_event_count"] == 2
    assert status["sequence"] == 2
    assert status["requires_human_approval"] is True
    assert status["executable"] is False
