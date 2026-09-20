from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .response_advisor import ResponseRecommendation


class ResponseApprovalState(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class IncidentResponseWorkflow:
    incident_id: str
    recommendations: tuple[ResponseRecommendation, ...]
    approval_state: ResponseApprovalState
    requires_human_approval: bool
    executable: bool


class IncidentApprovalWorkflow:
    def create(
        self,
        *,
        incident_id: str,
        recommendations: Iterable[ResponseRecommendation],
    ) -> IncidentResponseWorkflow:
        items = tuple(recommendations)

        requires = any(
            r.requires_human_approval
            for r in items
        )

        return IncidentResponseWorkflow(
            incident_id=incident_id,
            recommendations=items,
            approval_state=(
                ResponseApprovalState.PENDING
                if requires
                else ResponseApprovalState.NOT_REQUIRED
            ),
            requires_human_approval=requires,
            executable=False,
        )

    def approve(
        self,
        workflow: IncidentResponseWorkflow,
    ) -> IncidentResponseWorkflow:
        # Approval changes workflow state only.
        # It never executes a response.
        return IncidentResponseWorkflow(
            incident_id=workflow.incident_id,
            recommendations=workflow.recommendations,
            approval_state=ResponseApprovalState.APPROVED,
            requires_human_approval=workflow.requires_human_approval,
            executable=False,
        )

    def reject(
        self,
        workflow: IncidentResponseWorkflow,
    ) -> IncidentResponseWorkflow:
        return IncidentResponseWorkflow(
            incident_id=workflow.incident_id,
            recommendations=workflow.recommendations,
            approval_state=ResponseApprovalState.REJECTED,
            requires_human_approval=workflow.requires_human_approval,
            executable=False,
        )
