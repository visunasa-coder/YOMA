from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from yoma.office.action_approval import ActionApprovalWorkflow
from yoma.office.action_planning import ActionPlan
from yoma.office.execution_policy import ExecutionPolicyResult
from yoma.office.governance.policy import AuditLog


@dataclass(frozen=True)
class ExecutionAuditTrace:
    """
    Immutable trace linking policy, approval and execution state.
    """

    trace_id: str
    plan_id: str
    decision_id: str
    workflow_id: str
    approval_id: str | None
    action_id: str
    action_type: str
    policy_status: str
    execution_status: str
    executed: bool
    blocked: bool
    created_at: datetime
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trace_id.startswith("TRACE-"):
            raise ValueError("trace_id must start with TRACE-")

        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")

        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")

        if not self.workflow_id:
            raise ValueError("workflow_id is required")

        if not self.action_id:
            raise ValueError("action_id is required")

        if not self.action_type:
            raise ValueError("action_type is required")

        if self.policy_status not in {
            "allowed",
            "restricted",
            "blocked",
        }:
            raise ValueError("invalid policy status")

        if not self.requires_human_approval:
            raise ValueError(
                "execution audit traces must require human approval"
            )

        if self.blocked and self.executed:
            raise ValueError(
                "blocked execution cannot be marked executed"
            )


class ExecutionAuditRecorder:
    """
    M32.5 execution traceability layer.

    This component records what happened around a controlled execution
    attempt. It does not execute actions and does not make policy or
    approval decisions.
    """

    def __init__(
        self,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._audit_log = audit_log or AuditLog()
        self._traces: dict[str, ExecutionAuditTrace] = {}

    @property
    def audit_log(self) -> AuditLog:
        return self._audit_log

    @property
    def traces(self) -> tuple[ExecutionAuditTrace, ...]:
        return tuple(
            self._traces[key]
            for key in sorted(self._traces)
        )

    def get_trace(
        self,
        trace_id: str,
    ) -> ExecutionAuditTrace | None:
        return self._traces.get(trace_id)

    @staticmethod
    def _action_details(
        plan: ActionPlan,
    ) -> tuple[str, str]:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if not plan.steps:
            raise ValueError(
                "action plan contains no steps"
            )

        step = plan.steps[0]

        action_id = (
            getattr(step, "action_id", None)
            or getattr(step, "step_id", None)
        )
        action_type = getattr(
            step,
            "action_type",
            None,
        )

        if not action_id:
            raise ValueError(
                "action plan step has no action identifier"
            )

        if not action_type:
            raise ValueError(
                "action plan step has no action type"
            )

        return action_id, action_type

    @staticmethod
    def _approval_id(
        workflow: ActionApprovalWorkflow,
    ) -> str | None:
        if not isinstance(
            workflow,
            ActionApprovalWorkflow,
        ):
            raise TypeError(
                "workflow must be an ActionApprovalWorkflow"
            )

        if not workflow.approval_history:
            return None

        return workflow.approval_history[-1].approval_id

    def record(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        policy_result: ExecutionPolicyResult,
        actor: str,
        created_at: datetime,
    ) -> ExecutionAuditTrace:
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

        if not isinstance(
            policy_result,
            ExecutionPolicyResult,
        ):
            raise TypeError(
                "policy_result must be an ExecutionPolicyResult"
            )

        if not actor or not actor.strip():
            raise ValueError("actor is required")

        if workflow.plan_id != plan.plan_id:
            raise ValueError(
                "workflow and plan IDs do not match"
            )

        if workflow.decision_id != plan.decision_id:
            raise ValueError(
                "workflow and plan decision IDs do not match"
            )

        action_id, action_type = self._action_details(plan)
        approval_id = self._approval_id(workflow)

        trace_id = (
            f"TRACE-{workflow.workflow_id}-{action_id}"
        )

        if trace_id in self._traces:
            raise ValueError(
                f"audit trace already exists: {trace_id}"
            )

        execution_status = (
            policy_result.execution.status
            if policy_result.execution is not None
            else "blocked"
        )

        trace = ExecutionAuditTrace(
            trace_id=trace_id,
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            workflow_id=workflow.workflow_id,
            approval_id=approval_id,
            action_id=action_id,
            action_type=action_type,
            policy_status=policy_result.policy_check.status,
            execution_status=execution_status,
            executed=policy_result.executed,
            blocked=policy_result.blocked,
            created_at=created_at,
            requires_human_approval=True,
            metadata={
                "actor": actor,
                "policy_check_id": (
                    policy_result.policy_check.check_id
                ),
                "passed_constraint_count": (
                    policy_result.policy_check.passed_count
                ),
                "failed_constraint_count": (
                    policy_result.policy_check.failed_count
                ),
                "execution_id": (
                    policy_result.execution.execution_id
                    if policy_result.execution is not None
                    else None
                ),
            },
        )

        self._traces[trace_id] = trace

        audit_status = (
            "executed"
            if policy_result.executed
            else "blocked"
        )

        self._audit_log.record(
            audit_id=f"AUDIT-{trace_id}",
            event_type=f"execution.{audit_status}",
            actor=actor,
            request_id=workflow.workflow_id,
            action_type=action_type,
            status=audit_status,
            reason=policy_result.reason,
            metadata={
                "trace_id": trace_id,
                "plan_id": plan.plan_id,
                "decision_id": plan.decision_id,
                "workflow_id": workflow.workflow_id,
                "approval_id": approval_id,
                "policy_status": policy_result.policy_check.status,
                "execution_status": execution_status,
                "execution_id": (
                    policy_result.execution.execution_id
                    if policy_result.execution is not None
                    else None
                ),
            },
        )

        return trace

    def record_execution(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        policy_result: ExecutionPolicyResult,
        actor: str,
        created_at: datetime,
    ) -> ExecutionAuditTrace:
        return self.record(
            workflow=workflow,
            plan=plan,
            policy_result=policy_result,
            actor=actor,
            created_at=created_at,
        )
