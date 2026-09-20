from unittest.mock import Mock

import pytest

from yoma.office.distributed_edge_worker import (
    DistributedEdgeWorker,
    DistributedEdgeWorkerStatus,
    create_distributed_edge_worker,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)


def make_organization():
    return DistributedOrganizationIdentity(
        organization_id="org-1",
        organization_name="Jeeven Tech",
        deployment_id="deployment-1",
    )


def make_node():
    return DistributedNodeIdentity(
        node_id="node-1",
        organization_id="org-1",
        deployment_id="deployment-1",
        node_name="Employee-PC",
    )


def test_worker_creation():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    assert worker.organization.organization_id == "org-1"
    assert worker.node.node_id == "node-1"
    assert worker.running is False


def test_worker_uses_existing_runtime():
    runtime = Mock()
    runtime.status.return_value = type(
        "RuntimeStatus",
        (),
        {
            "runtime_state": "stopped",
            "running": False,
        },
    )()

    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
        runtime=runtime,
    )

    assert worker.runtime is runtime


def test_worker_start_delegates_to_host():
    runtime = Mock()
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
        runtime=runtime,
    )

    worker.start()

    runtime.start.assert_called_once()


def test_worker_stop_delegates_to_host():
    runtime = Mock()
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
        runtime=runtime,
    )

    worker.start()
    runtime.reset_mock()

    worker.stop()

    runtime.stop.assert_called_once()


def test_status_contains_node_identity():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    status = worker.status()

    assert isinstance(status, DistributedEdgeWorkerStatus)
    assert status.node_id == "node-1"
    assert status.organization_id == "org-1"
    assert status.deployment_id == "deployment-1"


def test_initial_status_is_stopped():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    status = worker.status()

    assert status.running is False
    assert status.state == "stopped"
    assert status.runtime_state == "stopped"


def test_start_and_stop_lifecycle():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    worker.start()

    assert worker.running is True
    assert worker.status().state == "running"

    worker.stop()

    assert worker.running is False
    assert worker.status().state == "stopped"


def test_start_is_idempotent():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    worker.start()
    worker.start()

    assert worker.running is True

    worker.stop()


def test_stop_is_idempotent():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    worker.stop()

    assert worker.running is False


def test_foreign_node_rejected():
    foreign_node = DistributedNodeIdentity(
        node_id="node-foreign",
        organization_id="org-2",
        deployment_id="deployment-2",
        node_name="Other-PC",
    )

    with pytest.raises(ValueError):
        DistributedEdgeWorker(
            organization=make_organization(),
            node=foreign_node,
        )


def test_invalid_organization_rejected():
    with pytest.raises(TypeError):
        DistributedEdgeWorker(
            organization=None,
            node=make_node(),
        )


def test_invalid_node_rejected():
    with pytest.raises(TypeError):
        DistributedEdgeWorker(
            organization=make_organization(),
            node=None,
        )


def test_status_governance_boundary():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    status = worker.status()

    assert status.requires_human_approval is True
    assert status.executable is False


def test_health_contains_identity():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    health = worker.health()

    assert health["node_id"] == "node-1"
    assert health["organization_id"] == "org-1"
    assert health["deployment_id"] == "deployment-1"


def test_health_is_governed():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    health = worker.health()

    assert health["requires_human_approval"] is True
    assert health["executable"] is False


def test_factory_creates_worker():
    worker = create_distributed_edge_worker(
        organization=make_organization(),
        node=make_node(),
    )

    assert isinstance(worker, DistributedEdgeWorker)


def test_factory_preserves_runtime():
    runtime = Mock()

    worker = create_distributed_edge_worker(
        organization=make_organization(),
        node=make_node(),
        runtime=runtime,
    )

    assert worker.runtime is runtime


def test_worker_does_not_create_execution_authority():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    assert not hasattr(worker, "approve")
    assert not hasattr(worker, "authorize")
    assert not hasattr(worker, "execute")


def test_worker_status_is_deterministic_when_stopped():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    first = worker.status()
    second = worker.status()

    assert first == second


def test_node_identity_remains_bound_to_organization():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    assert worker.node.belongs_to(worker.organization)


def test_worker_can_be_restarted():
    worker = DistributedEdgeWorker(
        organization=make_organization(),
        node=make_node(),
    )

    worker.start()
    worker.stop()
    worker.start()

    assert worker.running is True

    worker.stop()
