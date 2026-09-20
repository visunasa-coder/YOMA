"""Distributed node security and trust boundary for YOMA.

M45.7 establishes a secret-free trust boundary for distributed employee-PC
nodes. Trust validates identity and deployment membership; it never grants
execution authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from yoma.office.distributed_organization_identity import (
    DistributedNodeIdentity,
    DistributedOrganizationIdentity,
)


class NodeTrustState(str, Enum):
    UNKNOWN = "unknown"
    TRUSTED = "trusted"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass(frozen=True)
class DistributedNodeTrust:
    """Secret-free trust record for one distributed YOMA node."""

    node_id: str
    organization_id: str
    deployment_id: str
    state: NodeTrustState = NodeTrustState.UNKNOWN
    reason: str = ""
    registered_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("node_id", self.node_id),
            ("organization_id", self.organization_id),
            ("deployment_id", self.deployment_id),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} is required")

        if not isinstance(self.state, NodeTrustState):
            raise TypeError("state must be a NodeTrustState")

        for name, value in (
            ("registered_at", self.registered_at),
            ("updated_at", self.updated_at),
        ):
            if value is not None:
                if value.tzinfo is None:
                    raise ValueError(f"{name} must be timezone-aware")

    @property
    def trusted(self) -> bool:
        return self.state == NodeTrustState.TRUSTED

    @property
    def blocked(self) -> bool:
        return self.state in {
            NodeTrustState.SUSPENDED,
            NodeTrustState.REVOKED,
        }

    def as_dict(self) -> dict[str, Any]:
        """Return deterministic metadata without secrets."""
        return {
            "node_id": self.node_id,
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "state": self.state.value,
            "reason": self.reason,
            "registered_at": (
                self.registered_at.isoformat()
                if self.registered_at is not None
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at is not None
                else None
            ),
        }


@dataclass(frozen=True)
class DistributedNodeSecurityResult:
    """Result of distributed node security validation."""

    node_id: str
    organization_id: str
    deployment_id: str
    valid: bool
    state: NodeTrustState
    issues: tuple[str, ...] = ()
    trust: DistributedNodeTrust | None = None
    requires_human_approval: bool = True
    executable: bool = False
    execution_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id is required")
        if not self.organization_id:
            raise ValueError("organization_id is required")
        if not self.deployment_id:
            raise ValueError("deployment_id is required")

        if not isinstance(self.state, NodeTrustState):
            raise TypeError("state must be a NodeTrustState")

        if self.executable:
            raise ValueError(
                "distributed node security cannot authorize execution"
            )

        if self.execution_allowed:
            raise ValueError(
                "distributed node security cannot allow execution"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "distributed node security requires human approval"
            )

    @property
    def trusted(self) -> bool:
        return self.valid and self.state == NodeTrustState.TRUSTED

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "organization_id": self.organization_id,
            "deployment_id": self.deployment_id,
            "valid": self.valid,
            "state": self.state.value,
            "issues": list(self.issues),
            "trust": self.trust.as_dict() if self.trust else None,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
            "execution_allowed": self.execution_allowed,
        }


class DistributedNodeSecurityManager:
    """Governed security boundary for distributed YOMA nodes."""

    def __init__(
        self,
        *,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
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

        self.organization = organization
        self.node = node
        self._trust: DistributedNodeTrust | None = None

    @property
    def trust(self) -> DistributedNodeTrust | None:
        return self._trust

    def register(self) -> DistributedNodeTrust:
        """Register the node in UNKNOWN state without authorizing it."""
        now = datetime.now(timezone.utc)

        self._trust = DistributedNodeTrust(
            node_id=self.node.node_id,
            organization_id=self.node.organization_id,
            deployment_id=self.node.deployment_id,
            state=NodeTrustState.UNKNOWN,
            reason="node_registered_pending_trust",
            registered_at=now,
            updated_at=now,
        )
        return self._trust

    def validate(
        self,
        *,
        organization_id: str,
        deployment_id: str,
        node_id: str,
    ) -> DistributedNodeSecurityResult:
        """Validate node identity against the expected deployment."""
        issues: list[str] = []

        if organization_id != self.organization.organization_id:
            issues.append("organization mismatch")

        if deployment_id != self.organization.deployment_id:
            issues.append("deployment mismatch")

        if node_id != self.node.node_id:
            issues.append("node mismatch")

        if self._trust is None:
            state = NodeTrustState.UNKNOWN
            issues.append("node is not registered")
        else:
            state = self._trust.state

            if state == NodeTrustState.REVOKED:
                issues.append("node is revoked")
            elif state == NodeTrustState.SUSPENDED:
                issues.append("node is suspended")
            elif state != NodeTrustState.TRUSTED:
                issues.append("node is not trusted")

        return DistributedNodeSecurityResult(
            node_id=node_id,
            organization_id=organization_id,
            deployment_id=deployment_id,
            valid=not issues,
            state=state,
            issues=tuple(issues),
            trust=self._trust,
        )

    def trust_node(self, *, reason: str = "node_trusted") -> DistributedNodeTrust:
        """Explicitly trust the registered node."""
        if self._trust is None:
            self.register()

        assert self._trust is not None

        now = datetime.now(timezone.utc)

        self._trust = DistributedNodeTrust(
            node_id=self._trust.node_id,
            organization_id=self._trust.organization_id,
            deployment_id=self._trust.deployment_id,
            state=NodeTrustState.TRUSTED,
            reason=reason,
            registered_at=self._trust.registered_at,
            updated_at=now,
        )
        return self._trust

    def suspend_node(
        self,
        *,
        reason: str = "node_suspended",
    ) -> DistributedNodeTrust:
        """Suspend the node without deleting its identity."""
        if self._trust is None:
            self.register()

        assert self._trust is not None

        now = datetime.now(timezone.utc)

        self._trust = DistributedNodeTrust(
            node_id=self._trust.node_id,
            organization_id=self._trust.organization_id,
            deployment_id=self._trust.deployment_id,
            state=NodeTrustState.SUSPENDED,
            reason=reason,
            registered_at=self._trust.registered_at,
            updated_at=now,
        )
        return self._trust

    def revoke_node(
        self,
        *,
        reason: str = "node_revoked",
    ) -> DistributedNodeTrust:
        """Permanently revoke trust for the node."""
        if self._trust is None:
            self.register()

        assert self._trust is not None

        now = datetime.now(timezone.utc)

        self._trust = DistributedNodeTrust(
            node_id=self._trust.node_id,
            organization_id=self._trust.organization_id,
            deployment_id=self._trust.deployment_id,
            state=NodeTrustState.REVOKED,
            reason=reason,
            registered_at=self._trust.registered_at,
            updated_at=now,
        )
        return self._trust

    def status(self) -> dict[str, Any]:
        """Return secret-free security status."""
        return {
            "organization_id": self.organization.organization_id,
            "deployment_id": self.organization.deployment_id,
            "node_id": self.node.node_id,
            "trust_state": (
                self._trust.state.value
                if self._trust is not None
                else NodeTrustState.UNKNOWN.value
            ),
            "trusted": (
                self._trust.trusted
                if self._trust is not None
                else False
            ),
            "execution_allowed": False,
            "executable": False,
            "requires_human_approval": True,
        }


def create_distributed_node_security(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
) -> DistributedNodeSecurityManager:
    return DistributedNodeSecurityManager(
        organization=organization,
        node=node,
    )
