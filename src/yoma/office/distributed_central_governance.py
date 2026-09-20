from __future__ import annotations

"""M45.6 — Distributed Central Governance & Approval.

Central governance boundary for YOMA's distributed/no-server edition.

This module:
    - validates organization/deployment/node ownership
    - validates incoming ActionPlans
    - creates approval workflows through the existing M31 approval engine
    - exposes human approval operations
    - keeps execution outside this layer

It does NOT:
    - execute actions
    - authorize itself
    - bypass human approval
    - create a second approval engine
    - communicate directly with external systems
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from yoma.office.action_approval import (
    ActionApprovalEngine,
    ActionApprovalWorkflow,
)
from yoma.office.action_planning import ActionPlan

from .distributed_organization_identity import (
    DistributedOrganizationIdentity,
    DistributedNodeIdentity,
)


@dataclass(frozen=True)
class CentralGovernanceRequest:
    """A governed request originating from a distributed node."""

    request_id: str
    organization_id: str
    deployment_id: str
    node_id: str
    plan: ActionPlan
    requested_at: datetime
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id is required")

        if not self.organization_id:
            raise ValueError("organization_id is required")

        if not self.deployment_id:
            raise ValueError("deployment_id is required")

        if not self.node_id:
            raise ValueError("node_id is required")

        if not isinstance(self.plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class CentralGovernanceResult:
    """Result of central governance processing."""

    request_id: str
    organization_id: str
    deployment_id: str
    node_id: str
    workflow: ActionApprovalWorkflow
    governance_status: str
    validation_issues: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False
    execution_allowed: bool = False
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id is required")

        if self.governance_status not in {
            "approved_for_review",
            "rejected_by_governance",
        }:
            raise ValueError("invalid governance_status")

        if not self.requires_human_approval:
            raise ValueError(
                "distributed governance must retain human approval"
            )

        if self.executable:
            raise ValueError(
                "central governance cannot produce executable results"
            )

        if self.execution_allowed:
            raise ValueError(
                "central governance cannot authorize execution"
            )

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    @property
    def approval_pending(self) -> bool:
        return self.workflow.status == "pending"

    @property
    def approved(self) -> bool:
        return self.workflow.status == "approved"

    @property
    def rejected(self) -> bool:
        return self.workflow.status == "rejected"

    @property
    def modified(self) -> bool:
        return self.workflow.status == "modified"


class DistributedCentralGovernance:
    """Central governance runtime for distributed YOMA deployments.

    Governance is deliberately separate from execution.

    A distributed node can submit a plan, but the node cannot
    self-authorize it. Approval remains delegated to the existing
    ActionApprovalEngine.
    """

    def __init__(
        self,
        *,
        organization: DistributedOrganizationIdentity,
        node: DistributedNodeIdentity,
        approval_engine: Optional[ActionApprovalEngine] = None,
    ) -> None:
        if not isinstance(
            organization,
            DistributedOrganizationIdentity,
        ):
            raise TypeError(
                "organization must be a DistributedOrganizationIdentity"
            )

        if not isinstance(
            node,
            DistributedNodeIdentity,
        ):
            raise TypeError(
                "node must be a DistributedNodeIdentity"
            )

        if node.organization_id != organization.organization_id:
            raise ValueError(
                "node does not belong to the supplied organization"
            )

        if node.deployment_id != organization.deployment_id:
            raise ValueError(
                "node does not belong to the supplied deployment"
            )

        self.organization = organization
        self.node = node
        self.approval_engine = (
            approval_engine or ActionApprovalEngine()
        )

        self._requests: dict[str, CentralGovernanceRequest] = {}
        self._results: dict[str, CentralGovernanceResult] = {}

    def validate_request(
        self,
        request: CentralGovernanceRequest,
    ) -> Tuple[str, ...]:
        """Validate distributed ownership and ActionPlan consistency."""

        if not isinstance(request, CentralGovernanceRequest):
            raise TypeError(
                "request must be a CentralGovernanceRequest"
            )

        issues: list[str] = []

        if request.organization_id != self.organization.organization_id:
            issues.append("organization_id mismatch")

        if request.deployment_id != self.organization.deployment_id:
            issues.append("deployment_id mismatch")

        if request.node_id != self.node.node_id:
            issues.append("node_id mismatch")

        if request.plan.requires_human_approval is not True:
            issues.append(
                "ActionPlan must require human approval"
            )

        if request.plan.plan_id == "":
            issues.append("plan_id is required")

        if request.plan.decision_id == "":
            issues.append("decision_id is required")

        return tuple(issues)

    def submit(
        self,
        request: CentralGovernanceRequest,
    ) -> CentralGovernanceResult:
        """Submit a plan to the existing human approval infrastructure."""

        issues = self.validate_request(request)

        if issues:
            result = CentralGovernanceResult(
                request_id=request.request_id,
                organization_id=request.organization_id,
                deployment_id=request.deployment_id,
                node_id=request.node_id,
                workflow=self.approval_engine.create(request.plan),
                governance_status="rejected_by_governance",
                validation_issues=issues,
                requires_human_approval=True,
                executable=False,
                execution_allowed=False,
                metadata={
                    **dict(request.metadata),
                    "governance_source": "M45.6",
                    "governance": "rejected",
                },
            )

            self._requests[request.request_id] = request
            self._results[request.request_id] = result
            return result

        existing = self._results.get(request.request_id)
        if existing is not None:
            return existing

        workflow = self.approval_engine.create(request.plan)

        result = CentralGovernanceResult(
            request_id=request.request_id,
            organization_id=request.organization_id,
            deployment_id=request.deployment_id,
            node_id=request.node_id,
            workflow=workflow,
            governance_status="approved_for_review",
            validation_issues=(),
            requires_human_approval=True,
            executable=False,
            execution_allowed=False,
            metadata={
                **dict(request.metadata),
                "governance_source": "M45.6",
                "governance": "accepted_for_human_review",
            },
        )

        self._requests[request.request_id] = request
        self._results[request.request_id] = result

        return result

    def approve(
        self,
        request_id: str,
        *,
        reviewer_id: str,
        decided_at: datetime,
        comment: str = "",
    ) -> CentralGovernanceResult:
        """Record explicit human approval.

        Approval does not execute the plan.
        """

        if decided_at.tzinfo is None:
            raise ValueError(
                "decided_at must be timezone-aware"
            )

        request = self._requests.get(request_id)
        result = self._results.get(request_id)

        if request is None or result is None:
            raise KeyError(
                f"unknown governance request: {request_id}"
            )

        if result.governance_status != "approved_for_review":
            raise PermissionError(
                "governance request is not eligible for approval"
            )

        workflow = self.approval_engine.approve(
            result.workflow,
            reviewer_id,
            decided_at,
            comment,
        )

        updated = CentralGovernanceResult(
            request_id=result.request_id,
            organization_id=result.organization_id,
            deployment_id=result.deployment_id,
            node_id=result.node_id,
            workflow=workflow,
            governance_status="approved_for_review",
            validation_issues=result.validation_issues,
            requires_human_approval=True,
            executable=False,
            execution_allowed=False,
            metadata={
                **dict(result.metadata),
                "human_review": "approved",
                "execution_handoff": (
                    "existing_approval_execution_bridge"
                ),
            },
        )

        self._results[request_id] = updated
        return updated

    def reject(
        self,
        request_id: str,
        *,
        reviewer_id: str,
        decided_at: datetime,
        comment: str = "",
    ) -> CentralGovernanceResult:
        """Record explicit human rejection."""

        if decided_at.tzinfo is None:
            raise ValueError(
                "decided_at must be timezone-aware"
            )

        result = self._results.get(request_id)

        if result is None:
            raise KeyError(
                f"unknown governance request: {request_id}"
            )

        workflow = self.approval_engine.reject(
            result.workflow,
            reviewer_id,
            decided_at,
            comment,
        )

        updated = CentralGovernanceResult(
            request_id=result.request_id,
            organization_id=result.organization_id,
            deployment_id=result.deployment_id,
            node_id=result.node_id,
            workflow=workflow,
            governance_status="approved_for_review",
            validation_issues=result.validation_issues,
            requires_human_approval=True,
            executable=False,
            execution_allowed=False,
            metadata={
                **dict(result.metadata),
                "human_review": "rejected",
            },
        )

        self._results[request_id] = updated
        return updated

    def modify(
        self,
        request_id: str,
        *,
        reviewer_id: str,
        decided_at: datetime,
        modifications: Mapping[str, Any],
        comment: str = "",
    ) -> CentralGovernanceResult:
        """Record an explicit human modification."""

        if decided_at.tzinfo is None:
            raise ValueError(
                "decided_at must be timezone-aware"
            )

        result = self._results.get(request_id)

        if result is None:
            raise KeyError(
                f"unknown governance request: {request_id}"
            )

        workflow = self.approval_engine.modify(
            result.workflow,
            reviewer_id,
            decided_at,
            modifications,
            comment,
        )

        updated = CentralGovernanceResult(
            request_id=result.request_id,
            organization_id=result.organization_id,
            deployment_id=result.deployment_id,
            node_id=result.node_id,
            workflow=workflow,
            governance_status="approved_for_review",
            validation_issues=result.validation_issues,
            requires_human_approval=True,
            executable=False,
            execution_allowed=False,
            metadata={
                **dict(result.metadata),
                "human_review": "modified",
            },
        )

        self._results[request_id] = updated
        return updated

    def get(
        self,
        request_id: str,
    ) -> Optional[CentralGovernanceResult]:
        return self._results.get(request_id)

    @property
    def requests(
        self,
    ) -> Tuple[CentralGovernanceRequest, ...]:
        return tuple(self._requests.values())

    @property
    def results(
        self,
    ) -> Tuple[CentralGovernanceResult, ...]:
        return tuple(self._results.values())

    @property
    def executable(self) -> bool:
        return False

    @property
    def requires_human_approval(self) -> bool:
        return True

    @property
    def execution_allowed(self) -> bool:
        return False


def create_distributed_central_governance(
    *,
    organization: DistributedOrganizationIdentity,
    node: DistributedNodeIdentity,
    approval_engine: Optional[ActionApprovalEngine] = None,
) -> DistributedCentralGovernance:
    """Factory for the M45.6 governance runtime."""

    return DistributedCentralGovernance(
        organization=organization,
        node=node,
        approval_engine=approval_engine,
    )
