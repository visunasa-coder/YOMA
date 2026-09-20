"""Unified distributed runtime for YOMA M45.

M45.8 composes the distributed identity, node security, edge worker,
event collection, cloud synchronization, offline handling, and central
governance layers.

This runtime coordinates those boundaries but never grants execution
authorization and never creates a parallel execution path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yoma.office.cloud_sync import CloudSyncManager
from yoma.office.distributed_central_governance import (
    DistributedCentralGovernance,
)
from yoma.office.distributed_edge_worker import DistributedEdgeWorker
from yoma.office.distributed_event_collection import (
    DistributedEventCollector,
)
from yoma.office.distributed_node_security import (
    DistributedNodeSecurityManager,
)
from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)
from yoma.office.offline_connectivity import (
    OfflineConnectivityManager,
)
from yoma.office.runtime import YomaEmbeddedRuntime


@dataclass(frozen=True)
class DistributedRuntimeStatus:
    """Secret-free status of the complete distributed runtime."""

    organization_id: str
    deployment_id: str
    node_id: str
    running: bool
    runtime_state: str
    node_trusted: bool
    connectivity_state: str
    pending_sync_count: int
    executable: bool = False
    execution_allowed: bool = False
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.organization_id:
            raise ValueError("organization_id is required")
        if not self.deployment_id:
            raise ValueError("deployment_id is required")
        if not self.node_id:
            raise ValueError("node_id is required")

        if self.executable:
            raise ValueError(
                "distributed runtime cannot authorize execution"
            )

        if self.execution_allowed:
            raise ValueError(
                "distributed runtime cannot allow execution"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "distributed runtime requires human approval"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "node_id": self.node_id,
            "running": self.running,
            "runtime_state": self.runtime_state,
            "node_trusted": self.node_trusted,
            "connectivity_state": self.connectivity_state,
            "pending_sync_count": self.pending_sync_count,
            "executable": self.executable,
            "execution_allowed": self.execution_allowed,
            "requires_human_approval": self.requires_human_approval,
        }


class DistributedRuntime:
    """Unified governed runtime for the YOMA distributed/no-server edition."""

    def __init__(
        self,
        *,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
        embedded_runtime: YomaEmbeddedRuntime | None = None,
    ) -> None:
        if not isinstance(
            organization,
            DistributedOrganizationIdentity,
        ):
            raise TypeError(
                "organization must be DistributedOrganizationIdentity"
            )

        if not isinstance(node, DistributedNodeIdentity):
            raise TypeError(
                "node must be DistributedNodeIdentity"
            )

        if not node.belongs_to(organization):
            raise ValueError(
                "node does not belong to organization deployment"
            )

        if embedded_runtime is not None and not isinstance(
            embedded_runtime,
            YomaEmbeddedRuntime,
        ):
            raise TypeError(
                "embedded_runtime must be YomaEmbeddedRuntime or None"
            )

        self.organization = organization
        self.node = node

        self.security = DistributedNodeSecurityManager(
            organization=organization,
            node=node,
        )

        self.cloud_sync = CloudSyncManager(
            organization=organization,
            node=node,
        )

        self.event_collector = DistributedEventCollector(
            organization=organization,
            node=node,
            sync_manager=self.cloud_sync,
        )

        self.offline = OfflineConnectivityManager(
            organization=organization,
            node=node,
            sync_manager=self.cloud_sync,
        )

        self.governance = DistributedCentralGovernance(
            organization=organization,
            node=node,
        )

        self.edge_worker = DistributedEdgeWorker(
            organization=organization,
            node=node,
            runtime=embedded_runtime,
        )

        self._running = False

    @property
    def embedded_runtime(self) -> YomaEmbeddedRuntime:
        return self.edge_worker.runtime

    def start(self) -> None:
        """Start the existing embedded runtime through the edge worker."""
        if self._running:
            return

        self.edge_worker.start()
        self._running = True

    def stop(self) -> None:
        """Stop the edge worker and existing embedded runtime."""
        if not self._running:
            return

        try:
            self.edge_worker.stop()
        finally:
            self._running = False

    def register_node(self):
        """Register this node as pending trust."""
        return self.security.register()

    def trust_node(self, *, reason: str = "node_trusted"):
        """Explicitly establish node trust."""
        return self.security.trust_node(reason=reason)

    def validate_node(self):
        """Validate this runtime's organization/node binding."""
        return self.security.validate(
            organization_id=self.organization.organization_id,
            deployment_id=self.organization.deployment_id,
            node_id=self.node.node_id,
        )

    def collect_events(self, events):
        """Collect distributed events through the existing M45.4 boundary."""
        return self.event_collector.collect(events)

    def set_online(self) -> None:
        self.offline.set_online()

    def set_offline(self) -> None:
        self.offline.set_offline()

    def set_unknown_connectivity(self) -> None:
        self.offline.set_unknown()

    def status(self) -> DistributedRuntimeStatus:
        embedded = self.embedded_runtime.status()
        security = self.security.status()
        offline = self.offline.status()

        return DistributedRuntimeStatus(
            organization_id=self.organization.organization_id,
            deployment_id=self.organization.deployment_id,
            node_id=self.node.node_id,
            running=self._running,
            runtime_state=embedded.runtime_state,
            node_trusted=security["trusted"],
            connectivity_state=offline.state.value,
            pending_sync_count=offline.pending_count,
        )

    def diagnostics(self) -> dict[str, Any]:
        """Return composed, secret-free distributed diagnostics."""
        return {
            "organization": {
                "organization_id": self.organization.organization_id,
                "deployment_id": self.organization.deployment_id,
                "edition": self.organization.edition,
            },
            "node": {
                "node_id": self.node.node_id,
                "node_name": self.node.node_name,
                "node_type": self.node.node_type,
            },
            "runtime": self.embedded_runtime.status(),
            "edge_worker": self.edge_worker.status(),
            "security": self.security.status(),
            "event_collection": self.event_collector.status(),
            "cloud_sync": self.cloud_sync.status(),
            "offline": self.offline.status(),
            "governance": {
                "organization_id": self.organization.organization_id,
                "deployment_id": self.organization.deployment_id,
                "node_id": self.node.node_id,
                "execution_allowed": False,
                "executable": False,
                "requires_human_approval": True,
            },
            "execution": {
                "executable": False,
                "execution_allowed": False,
                "requires_human_approval": True,
            },
        }


def create_distributed_runtime(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
    embedded_runtime: YomaEmbeddedRuntime | None = None,
) -> DistributedRuntime:
    return DistributedRuntime(
        organization=organization,
        node=node,
        embedded_runtime=embedded_runtime,
    )
