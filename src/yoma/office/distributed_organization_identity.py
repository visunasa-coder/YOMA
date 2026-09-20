from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DistributedOrganizationIdentity:
    organization_id: str
    organization_name: str
    deployment_id: str
    edition: str = "distributed"

    def __post_init__(self) -> None:
        for field_name in (
            "organization_id",
            "organization_name",
            "deployment_id",
            "edition",
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
            f"{self.deployment_id}"
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "deployment_id": self.deployment_id,
            "edition": self.edition,
        }


@dataclass(frozen=True)
class DistributedNodeIdentity:
    node_id: str
    organization_id: str
    deployment_id: str
    node_name: str
    node_type: str = "employee_pc"

    def __post_init__(self) -> None:
        for field_name in (
            "node_id",
            "organization_id",
            "deployment_id",
            "node_name",
            "node_type",
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

    def belongs_to(
        self,
        organization: DistributedOrganizationIdentity,
    ) -> bool:
        return (
            self.organization_id == organization.organization_id
            and self.deployment_id == organization.deployment_id
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
        }


@dataclass(frozen=True)
class DistributedOrganizationAnalysis:
    organization_id: str
    deployment_id: str
    node_count: int
    valid: bool
    issues: tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False


class DistributedOrganizationIdentityManager:
    def analyze(
        self,
        organization: DistributedOrganizationIdentity,
        nodes: tuple[DistributedNodeIdentity, ...] = (),
    ) -> DistributedOrganizationAnalysis:
        if not isinstance(
            organization,
            DistributedOrganizationIdentity,
        ):
            raise TypeError(
                "organization must be a "
                "DistributedOrganizationIdentity"
            )

        if not isinstance(nodes, tuple):
            raise TypeError("nodes must be a tuple")

        issues: list[str] = []
        seen_nodes: set[str] = set()

        for node in nodes:
            if not isinstance(
                node,
                DistributedNodeIdentity,
            ):
                raise TypeError(
                    "all nodes must be "
                    "DistributedNodeIdentity instances"
                )

            if not node.belongs_to(organization):
                issues.append(
                    f"node {node.node_id} does not belong "
                    "to the organization deployment"
                )

            if node.node_id in seen_nodes:
                issues.append(
                    f"duplicate node_id: {node.node_id}"
                )

            seen_nodes.add(node.node_id)

        return DistributedOrganizationAnalysis(
            organization_id=organization.organization_id,
            deployment_id=organization.deployment_id,
            node_count=len(nodes),
            valid=not issues,
            issues=tuple(issues),
        )


def analyze_distributed_organization(
    organization: DistributedOrganizationIdentity,
    nodes: tuple[DistributedNodeIdentity, ...] = (),
) -> DistributedOrganizationAnalysis:
    return DistributedOrganizationIdentityManager().analyze(
        organization,
        nodes,
    )
