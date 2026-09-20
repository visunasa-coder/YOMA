from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from yoma.office.action_planning import ActionPlan


VALID_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "modified",
}


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    plan_id: str
    decision_id: str
    status: str
    decided_at: datetime
    reviewer_id: str
    comment: str = ""
    modifications: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.approval_id.startswith("APP-"):
            raise ValueError("approval_id must start with APP-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if self.status not in VALID_STATUSES:
            raise ValueError("invalid approval status")
        if not self.reviewer_id:
            raise ValueError("reviewer_id must not be empty")

        if self.status == "modified" and not self.modifications:
            raise ValueError(
                "modified approvals must contain modifications"
            )


@dataclass(frozen=True)
class ActionApprovalWorkflow:
    workflow_id: str
    plan_id: str
    decision_id: str
    status: str = "pending"
    approval_history: Tuple[ApprovalRecord, ...] = ()
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.workflow_id.startswith("AWF-"):
            raise ValueError("workflow_id must start with AWF-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if self.status not in VALID_STATUSES:
            raise ValueError("invalid workflow status")
        if not self.requires_human_approval:
            raise ValueError(
                "approval workflow requires human approval"
            )

    @property
    def pending(self) -> bool:
        return self.status == "pending"

    @property
    def approved(self) -> bool:
        return self.status == "approved"

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"

    @property
    def modified(self) -> bool:
        return self.status == "modified"

    @property
    def review_count(self) -> int:
        return len(self.approval_history)

    @property
    def executable(self) -> bool:
        return False


class ActionApprovalEngine:
    """
    Human approval state machine for advisory ActionPlans.

    This module records approval decisions only.
    It never executes an ActionPlan.
    """

    def create(self, plan: ActionPlan) -> ActionApprovalWorkflow:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        return ActionApprovalWorkflow(
            workflow_id=f"AWF-{plan.plan_id}",
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            status="pending",
            approval_history=(),
            requires_human_approval=True,
        )

    def approve(
        self,
        workflow: ActionApprovalWorkflow,
        reviewer_id: str,
        decided_at: datetime,
        comment: str = "",
    ) -> ActionApprovalWorkflow:
        return self._decide(
            workflow,
            reviewer_id,
            decided_at,
            "approved",
            comment,
            {},
        )

    def reject(
        self,
        workflow: ActionApprovalWorkflow,
        reviewer_id: str,
        decided_at: datetime,
        comment: str = "",
    ) -> ActionApprovalWorkflow:
        return self._decide(
            workflow,
            reviewer_id,
            decided_at,
            "rejected",
            comment,
            {},
        )

    def modify(
        self,
        workflow: ActionApprovalWorkflow,
        reviewer_id: str,
        decided_at: datetime,
        modifications: Mapping[str, Any],
        comment: str = "",
    ) -> ActionApprovalWorkflow:
        if not modifications:
            raise ValueError(
                "modifications must not be empty"
            )

        return self._decide(
            workflow,
            reviewer_id,
            decided_at,
            "modified",
            comment,
            dict(modifications),
        )

    def _decide(
        self,
        workflow: ActionApprovalWorkflow,
        reviewer_id: str,
        decided_at: datetime,
        status: str,
        comment: str,
        modifications: Mapping[str, Any],
    ) -> ActionApprovalWorkflow:
        if not isinstance(workflow, ActionApprovalWorkflow):
            raise TypeError(
                "workflow must be an ActionApprovalWorkflow"
            )

        if not reviewer_id:
            raise ValueError("reviewer_id must not be empty")

        if not workflow.pending:
            raise ValueError(
                "only pending workflows can receive a new decision"
            )

        record = ApprovalRecord(
            approval_id=(
                f"APP-{workflow.workflow_id}"
                f"-{len(workflow.approval_history) + 1}"
            ),
            plan_id=workflow.plan_id,
            decision_id=workflow.decision_id,
            status=status,
            decided_at=decided_at,
            reviewer_id=reviewer_id,
            comment=comment,
            modifications=dict(modifications),
        )

        return ActionApprovalWorkflow(
            workflow_id=workflow.workflow_id,
            plan_id=workflow.plan_id,
            decision_id=workflow.decision_id,
            status=status,
            approval_history=(
                *workflow.approval_history,
                record,
            ),
            requires_human_approval=True,
            metadata=dict(workflow.metadata),
        )
