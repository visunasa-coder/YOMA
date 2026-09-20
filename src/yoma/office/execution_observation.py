from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Tuple

from yoma.office.action_approval import ActionApprovalWorkflow
from yoma.office.action_planning import ActionPlan
from yoma.office.closed_loop_observation import (
    ClosedLoopObservation,
    ClosedLoopObservationEngine,
)
from yoma.office.execution_audit import ExecutionAuditTrace
from yoma.office.execution_policy import ExecutionPolicyResult


VALID_EXECUTION_OUTCOMES = {
    "succeeded",
    "failed",
    "rejected",
    "blocked",
    "unknown",
}


@dataclass(frozen=True)
class ExecutionResultObservation:
    observation_id: str
    trace_id: str
    execution_id: str | None
    workflow_id: str
    plan_id: str
    decision_id: str
    action_id: str
    action_type: str
    observed_at: datetime
    execution_status: str
    outcome_status: str
    success: bool
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    event_ids: Tuple[str, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.observation_id.startswith("EXOBS-"):
            raise ValueError("observation_id must start with EXOBS-")
        if not self.trace_id.startswith("TRACE-"):
            raise ValueError("trace_id must start with TRACE-")
        if not self.workflow_id.startswith("AWF-"):
            raise ValueError("workflow_id must start with AWF-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if not self.action_id:
            raise ValueError("action_id is required")
        if not self.action_type:
            raise ValueError("action_type is required")
        if self.execution_status not in {
            "succeeded",
            "failed",
            "rejected",
            "blocked",
        }:
            raise ValueError("invalid execution status")
        if self.outcome_status not in VALID_EXECUTION_OUTCOMES:
            raise ValueError("invalid outcome status")
        if not self.requires_human_approval:
            raise ValueError(
                "execution result observation requires human approval"
            )

    @property
    def observed(self) -> bool:
        return self.outcome_status != "unknown"

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def executable(self) -> bool:
        return False


class ExecutionResultObservationEngine:
    """
    M32.6 post-execution observation layer.

    Converts an already-recorded execution/audit result into an immutable
    observation and optionally feeds that observation into the existing
    M31.7 closed-loop observation system.

    This component never executes an action and never changes approval or
    policy state.
    """

    def __init__(
        self,
        closed_loop_engine: ClosedLoopObservationEngine | None = None,
    ) -> None:
        self._closed_loop_engine = (
            closed_loop_engine or ClosedLoopObservationEngine()
        )
        self._observations: dict[str, ExecutionResultObservation] = {}

    @property
    def observations(self) -> tuple[ExecutionResultObservation, ...]:
        return tuple(
            self._observations[key]
            for key in sorted(self._observations)
        )

    def get_observation(
        self,
        observation_id: str,
    ) -> ExecutionResultObservation | None:
        return self._observations.get(observation_id)

    @staticmethod
    def _action_details(plan: ActionPlan) -> tuple[str, str]:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")
        if not plan.steps:
            raise ValueError("action plan contains no steps")

        step = plan.steps[0]

        action_id = (
            getattr(step, "action_id", None)
            or getattr(step, "step_id", None)
        )
        action_type = getattr(step, "action_type", None)

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
    def _outcome_status(
        policy_result: ExecutionPolicyResult,
    ) -> tuple[str, bool, str | None]:

        if policy_result.blocked:
            return "blocked", False, policy_result.reason

        if policy_result.execution is None:
            return "unknown", False, policy_result.reason

        execution = policy_result.execution

        if execution.status == "succeeded":
            return "succeeded", True, execution.error

        if execution.status == "failed":
            return "failed", False, execution.error

        if execution.status == "rejected":
            return "rejected", False, execution.error

        return "unknown", False, execution.error

    def observe(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        policy_result: ExecutionPolicyResult,
        audit_trace: ExecutionAuditTrace,
        observed_at: datetime,
        event_ids: Tuple[str, ...] | list[str] = (),
        evidence: Mapping[str, Any] | None = None,
    ) -> ExecutionResultObservation:

        if not isinstance(workflow, ActionApprovalWorkflow):
            raise TypeError(
                "workflow must be an ActionApprovalWorkflow"
            )

        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if not isinstance(policy_result, ExecutionPolicyResult):
            raise TypeError(
                "policy_result must be an ExecutionPolicyResult"
            )

        if not isinstance(audit_trace, ExecutionAuditTrace):
            raise TypeError(
                "audit_trace must be an ExecutionAuditTrace"
            )

        if workflow.plan_id != plan.plan_id:
            raise ValueError(
                "workflow and plan IDs do not match"
            )

        if workflow.decision_id != plan.decision_id:
            raise ValueError(
                "workflow and plan decision IDs do not match"
            )

        if audit_trace.plan_id != plan.plan_id:
            raise ValueError(
                "audit trace and plan IDs do not match"
            )

        if audit_trace.decision_id != plan.decision_id:
            raise ValueError(
                "audit trace and plan decision IDs do not match"
            )

        if audit_trace.workflow_id != workflow.workflow_id:
            raise ValueError(
                "audit trace and workflow IDs do not match"
            )

        action_id, action_type = self._action_details(plan)

        if audit_trace.action_id != action_id:
            raise ValueError(
                "audit trace and plan action IDs do not match"
            )

        if audit_trace.action_type != action_type:
            raise ValueError(
                "audit trace and plan action types do not match"
            )

        outcome_status, success, error = self._outcome_status(
            policy_result
        )

        execution_id = (
            policy_result.execution.execution_id
            if policy_result.execution is not None
            else None
        )

        observation_id = f"EXOBS-{audit_trace.trace_id}"

        if observation_id in self._observations:
            raise ValueError(
                f"execution observation already exists: {observation_id}"
            )

        metadata = dict(evidence or {})

        metadata.update(
            {
                "policy_status": policy_result.policy_check.status,
                "executed": policy_result.executed,
                "blocked": policy_result.blocked,
                "audit_trace_id": audit_trace.trace_id,
                "execution_id": execution_id,
            }
        )

        output: Mapping[str, Any] = {}

        if policy_result.execution is not None:
            output = dict(policy_result.execution.output)

        observation = ExecutionResultObservation(
            observation_id=observation_id,
            trace_id=audit_trace.trace_id,
            execution_id=execution_id,
            workflow_id=workflow.workflow_id,
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            action_id=action_id,
            action_type=action_type,
            observed_at=observed_at,
            execution_status=(
                policy_result.execution.status
                if policy_result.execution is not None
                else (
                    "blocked"
                    if policy_result.blocked
                    else audit_trace.execution_status
                )
            ),
            outcome_status=outcome_status,
            success=success,
            output=output,
            error=error,
            event_ids=tuple(dict.fromkeys(event_ids)),
            evidence=metadata,
            requires_human_approval=True,
        )

        self._observations[observation_id] = observation

        return observation

    def observe_closed_loop(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        execution_observation: ExecutionResultObservation,
        expected_event_count: int = 1,
    ) -> ClosedLoopObservation:

        if not isinstance(workflow, ActionApprovalWorkflow):
            raise TypeError(
                "workflow must be an ActionApprovalWorkflow"
            )

        if not isinstance(
            execution_observation,
            ExecutionResultObservation,
        ):
            raise TypeError(
                "execution_observation must be an "
                "ExecutionResultObservation"
            )

        if workflow.workflow_id != execution_observation.workflow_id:
            raise ValueError(
                "workflow and execution observation IDs do not match"
            )

        loop = self._closed_loop_engine.create(
            workflow,
            expected_event_count=expected_event_count,
        )

        return self._closed_loop_engine.record(
            loop,
            observed_at=execution_observation.observed_at,
            outcome_status=(
                "observed"
                if execution_observation.success
                else "failed"
                if execution_observation.outcome_status == "failed"
                else "unknown"
                if execution_observation.outcome_status == "unknown"
                else "partial"
            ),
            description=(
                f"Execution {execution_observation.execution_status} "
                f"for {execution_observation.action_type}."
            ),
            event_ids=execution_observation.event_ids,
            evidence={
                "execution_observation_id": (
                    execution_observation.observation_id
                ),
                "execution_id": execution_observation.execution_id,
                "execution_status": (
                    execution_observation.execution_status
                ),
                "success": execution_observation.success,
            },
        )

    def observe_many(
        self,
        records,
    ) -> tuple[ExecutionResultObservation, ...]:

        return tuple(
            self.observe(
                workflow=workflow,
                plan=plan,
                policy_result=policy_result,
                audit_trace=audit_trace,
                observed_at=observed_at,
            )
            for (
                workflow,
                plan,
                policy_result,
                audit_trace,
                observed_at,
            ) in records
        )
