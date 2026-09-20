from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from yoma.office.action_approval import ActionApprovalWorkflow
from yoma.office.action_execution import (
    ActionExecutionGateway,
    ExecutionResult,
)
from yoma.office.action_planning import ActionPlan


@dataclass(frozen=True)
class GovernedExecutionResult:
    execution: ExecutionResult
    workflow_id: str
    approval_id: str
    approved: bool
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.workflow_id:
            raise ValueError("workflow_id is required")

        if not self.approval_id:
            raise ValueError("approval_id is required")

        if not self.approved:
            raise ValueError(
                "governed execution result requires approval"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "human approval must remain required"
            )

    @property
    def execution_id(self) -> str:
        return self.execution.execution_id

    @property
    def status(self) -> str:
        return self.execution.status

    @property
    def executable(self) -> bool:
        return self.execution.executable


class ApprovalExecutionBridge:
    """
    Bridges an existing M31 approval workflow to the M32
    execution gateway.

    The bridge does not create approval and does not infer
    authorization. It validates the workflow state and forwards
    the explicitly supplied ActionPlan to the execution gateway.
    """

    def __init__(
        self,
        gateway: ActionExecutionGateway,
    ) -> None:
        if not isinstance(gateway, ActionExecutionGateway):
            raise TypeError(
                "gateway must be an ActionExecutionGateway"
            )

        self._gateway = gateway

    @property
    def gateway(self) -> ActionExecutionGateway:
        return self._gateway

    @staticmethod
    def _approval_details(
        workflow: ActionApprovalWorkflow,
    ) -> tuple[str, bool]:
        if workflow.status != "approved":
            raise PermissionError(
                "execution requires an approved workflow"
            )

        history = tuple(workflow.approval_history)

        if not history:
            raise ValueError(
                "approved workflow has no approval history"
            )

        approval = history[-1]

        approval_id = getattr(
            approval,
            "approval_id",
            None,
        )

        if not approval_id:
            raise ValueError(
                "approval history record has no approval_id"
            )

        return approval_id, True

    @staticmethod
    def _action_details(
        plan: ActionPlan,
    ) -> tuple[str, str, Mapping[str, Any]]:
        if not isinstance(plan, ActionPlan):
            raise TypeError(
                "plan must be an ActionPlan"
            )

        steps = tuple(plan.steps)

        if not steps:
            raise ValueError(
                "action plan contains no steps"
            )

        step = steps[0]

        action_id = getattr(
            step,
            "action_id",
            None,
        )

        if not action_id:
            action_id = getattr(
                step,
                "step_id",
                None,
            )

        action_type = getattr(
            step,
            "action_type",
            None,
        )

        parameters = getattr(
            step,
            "parameters",
            {},
        )

        if not action_id:
            raise ValueError(
                "action plan step has no action identifier"
            )

        if not action_type:
            raise ValueError(
                "action plan step has no action type"
            )

        return (
            action_id,
            action_type,
            dict(parameters or {}),
        )

    def execute_approved(
        self,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        *,
        executor_name: str,
        created_at: datetime,
    ) -> GovernedExecutionResult:
        if not isinstance(
            workflow,
            ActionApprovalWorkflow,
        ):
            raise TypeError(
                "workflow must be an ActionApprovalWorkflow"
            )

        if not isinstance(plan, ActionPlan):
            raise TypeError(
                "plan must be an ActionPlan"
            )

        if workflow.plan_id != plan.plan_id:
            raise ValueError(
                "workflow and plan IDs do not match"
            )

        if workflow.decision_id != plan.decision_id:
            raise ValueError(
                "workflow and plan decision IDs do not match"
            )

        approval_id, approved = self._approval_details(
            workflow
        )

        action_id, action_type, parameters = (
            self._action_details(plan)
        )

        execution = self._gateway.execute_approved(
            action_id=action_id,
            action_type=action_type,
            executor_name=executor_name,
            created_at=created_at,
            parameters=parameters,
        )

        return GovernedExecutionResult(
            execution=execution,
            workflow_id=workflow.workflow_id,
            approval_id=approval_id,
            approved=approved,
            requires_human_approval=True,
        )

    def execute(
        self,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        *,
        executor_name: str,
        created_at: datetime,
    ) -> GovernedExecutionResult:
        return self.execute_approved(
            workflow,
            plan,
            executor_name=executor_name,
            created_at=created_at,
        )
