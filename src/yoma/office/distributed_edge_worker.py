from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)
from yoma.office.runtime import YomaEmbeddedRuntime
from yoma.office.service_host import ServiceHost


@dataclass(frozen=True)
class DistributedEdgeWorkerStatus:
    node_id: str
    organization_id: str
    deployment_id: str
    state: str
    running: bool
    runtime_state: str
    requires_human_approval: bool = True
    executable: bool = False


class DistributedEdgeWorker:
    """Governed YOMA worker running on an employee PC."""

    def __init__(
        self,
        *,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
        runtime: YomaEmbeddedRuntime | None = None,
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
        self.runtime = runtime or YomaEmbeddedRuntime()
        self.host = ServiceHost(self.runtime)

    @property
    def running(self) -> bool:
        return self.host.running

    def start(self) -> None:
        self.host.start()

    def stop(self) -> None:
        self.host.stop()

    def status(self) -> DistributedEdgeWorkerStatus:
        host_status = self.host.status()

        return DistributedEdgeWorkerStatus(
            node_id=self.node.node_id,
            organization_id=self.organization.organization_id,
            deployment_id=self.organization.deployment_id,
            state=host_status["state"],
            running=self.running,
            runtime_state=host_status["runtime_state"],
        )

    def health(self) -> dict[str, Any]:
        health = self.host.health()

        return {
            **health,
            "node_id": self.node.node_id,
            "organization_id": self.organization.organization_id,
            "deployment_id": self.organization.deployment_id,
            "requires_human_approval": True,
            "executable": False,
        }


def create_distributed_edge_worker(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
    runtime: YomaEmbeddedRuntime | None = None,
) -> DistributedEdgeWorker:
    return DistributedEdgeWorker(
        organization=organization,
        node=node,
        runtime=runtime,
    )
