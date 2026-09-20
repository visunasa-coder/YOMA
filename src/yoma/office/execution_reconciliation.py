from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from .action_planning import ActionPlan
from .action_approval import ActionApprovalWorkflow
from .execution_audit import ExecutionAuditTrace
from .execution_observation import ExecutionResultObservation


VALID_RECONCILIATION_STATUSES = {
    "achieved",
    "partially_achieved",
    "failed",
    "unexpected",
    "insufficient_evidence",
}


@dataclass(frozen=True)
class ExecutionOutcomeReconciliation:
    reconciliation_id: str
    trace_id: str
    execution_id: Optional[str]
    workflow_id: str
    plan_id: str
    decision_id: str
    action_id: str
    action_type: str
    execution_status: str
    observed_outcome_status: str
    expected_event_count: int
    observed_event_count: int
    status: str
    expected_success: Optional[bool] = None
    observed_success: Optional[bool] = None
    variance: Mapping[str, Any] = field(default_factory=dict)
    evidence: Mapping[str, Any] = field(default_factory=dict)
    event_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.reconciliation_id:
            raise ValueError("reconciliation_id must not be empty")
        if not self.reconciliation_id.startswith("RECON-"):
            raise ValueError("reconciliation_id must start with RECON-")
        if not self.trace_id:
            raise ValueError("trace_id must not be empty")
        if not self.workflow_id:
            raise ValueError("workflow_id must not be empty")
        if not self.plan_id:
            raise ValueError("plan_id must not be empty")
        if not self.decision_id:
            raise ValueError("decision_id must not be empty")
        if not self.action_id:
            raise ValueError("action_id must not be empty")
        if not self.action_type:
            raise ValueError("action_type must not be empty")
        if self.expected_event_count < 0:
            raise ValueError("expected_event_count must be >= 0")
        if self.observed_event_count < 0:
            raise ValueError("observed_event_count must be >= 0")
        if self.status not in VALID_RECONCILIATION_STATUSES:
            raise ValueError(f"invalid reconciliation status: {self.status}")
        if not self.requires_human_approval:
            raise ValueError(
                "execution outcome reconciliation must require human approval"
            )

    @property
    def achieved(self) -> bool:
        return self.status == "achieved"

    @property
    def partially_achieved(self) -> bool:
        return self.status == "partially_achieved"

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    @property
    def requires_review(self) -> bool:
        return self.status != "achieved"

    @property
    def executable(self) -> bool:
        return False


class ExecutionOutcomeReconciliationEngine:
    """
    Reconciles an observed execution outcome against the expected outcome.

    This component is analytical only. It never executes, retries, modifies,
    or autonomously corrects an action.
    """

    def __init__(self) -> None:
        self._reconciliations: dict[
            str, ExecutionOutcomeReconciliation
        ] = {}

    @property
    def reconciliations(self) -> Tuple[
        ExecutionOutcomeReconciliation, ...
    ]:
        return tuple(self._reconciliations.values())

    def get_reconciliation(
        self,
        reconciliation_id: str,
    ) -> Optional[ExecutionOutcomeReconciliation]:
        return self._reconciliations.get(reconciliation_id)

    @staticmethod
    def _action_details(
        plan: ActionPlan,
    ) -> tuple[str, str]:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if not plan.steps:
            raise ValueError("action plan must contain at least one step")

        step = plan.steps[0]

        action_id = (
            getattr(step, "action_id", None)
            or getattr(step, "step_id", None)
        )
        action_type = getattr(step, "action_type", None)

        if not action_id:
            raise ValueError("action plan step must contain an action identifier")
        if not action_type:
            raise ValueError("action plan step must contain action_type")

        return action_id, action_type

    @staticmethod
    def _status(
        observation: ExecutionResultObservation,
        expected_event_count: int,
        expected_success: Optional[bool],
    ) -> str:
        observed_event_count = len(observation.event_ids)

        if observation.execution_status == "blocked":
            return "unexpected"

        if observation.execution_status == "rejected":
            return "unexpected"

        if observation.execution_status == "failed":
            return "failed"

        if observation.outcome_status == "unknown":
            return "insufficient_evidence"

        if expected_success is not None:
            if observation.success != expected_success:
                if observation.success:
                    return "unexpected"
                return "failed"

        if expected_event_count > 0:
            if observed_event_count == 0:
                return "insufficient_evidence"

            if observed_event_count < expected_event_count:
                return "partially_achieved"

        if observation.success:
            return "achieved"

        return "failed"

    def reconcile(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        audit_trace: ExecutionAuditTrace,
        observation: ExecutionResultObservation,
        expected_event_count: int = 0,
        expected_success: Optional[bool] = True,
        evidence: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionOutcomeReconciliation:
        if not isinstance(workflow, ActionApprovalWorkflow):
            raise TypeError("workflow must be an ActionApprovalWorkflow")

        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if not isinstance(audit_trace, ExecutionAuditTrace):
            raise TypeError("audit_trace must be an ExecutionAuditTrace")

        if not isinstance(observation, ExecutionResultObservation):
            raise TypeError(
                "observation must be an ExecutionResultObservation"
            )

        if expected_event_count < 0:
            raise ValueError("expected_event_count must be >= 0")

        if workflow.plan_id != plan.plan_id:
            raise ValueError("workflow and plan IDs do not match")

        if workflow.decision_id != plan.decision_id:
            raise ValueError("workflow and plan decision IDs do not match")

        if audit_trace.plan_id != plan.plan_id:
            raise ValueError("audit trace and plan IDs do not match")

        if audit_trace.workflow_id != workflow.workflow_id:
            raise ValueError(
                "audit trace and workflow IDs do not match"
            )

        if observation.trace_id != audit_trace.trace_id:
            raise ValueError(
                "observation and audit trace IDs do not match"
            )

        if observation.workflow_id != workflow.workflow_id:
            raise ValueError(
                "observation and workflow IDs do not match"
            )

        if observation.plan_id != plan.plan_id:
            raise ValueError(
                "observation and plan IDs do not match"
            )

        action_id, action_type = self._action_details(plan)

        if observation.action_id != action_id:
            raise ValueError(
                "observation and plan action IDs do not match"
            )

        if observation.action_type != action_type:
            raise ValueError(
                "observation and plan action types do not match"
            )

        reconciliation_id = f"RECON-{audit_trace.trace_id}"

        if reconciliation_id in self._reconciliations:
            raise ValueError(
                f"reconciliation already exists: {reconciliation_id}"
            )

        observed_event_count = len(observation.event_ids)

        status = self._status(
            observation,
            expected_event_count,
            expected_success,
        )

        variance = {
            "expected_success": expected_success,
            "observed_success": observation.success,
            "expected_event_count": expected_event_count,
            "observed_event_count": observed_event_count,
            "event_count_delta": (
                observed_event_count - expected_event_count
            ),
            "execution_status": observation.execution_status,
            "observed_outcome_status": observation.outcome_status,
        }

        combined_evidence = {
            "trace_id": audit_trace.trace_id,
            "execution_id": observation.execution_id,
            "workflow_id": workflow.workflow_id,
            "plan_id": plan.plan_id,
            "decision_id": plan.decision_id,
            "observation_id": observation.observation_id,
            "policy_status": audit_trace.policy_status,
        }

        if evidence:
            combined_evidence.update(dict(evidence))

        result = ExecutionOutcomeReconciliation(
            reconciliation_id=reconciliation_id,
            trace_id=audit_trace.trace_id,
            execution_id=observation.execution_id,
            workflow_id=workflow.workflow_id,
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            action_id=action_id,
            action_type=action_type,
            execution_status=observation.execution_status,
            observed_outcome_status=observation.outcome_status,
            expected_event_count=expected_event_count,
            observed_event_count=observed_event_count,
            status=status,
            expected_success=expected_success,
            observed_success=observation.success,
            variance=variance,
            evidence=combined_evidence,
            event_ids=tuple(observation.event_ids),
            requires_human_approval=True,
        )

        self._reconciliations[reconciliation_id] = result
        return result

    def reconcile_many(
        self,
        records,
    ) -> Tuple[ExecutionOutcomeReconciliation, ...]:
        return tuple(
            self.reconcile(
                workflow=workflow,
                plan=plan,
                audit_trace=audit_trace,
                observation=observation,
                expected_event_count=expected_event_count,
                expected_success=expected_success,
                evidence=evidence,
            )
            for (
                workflow,
                plan,
                audit_trace,
                observation,
                expected_event_count,
                expected_success,
                evidence,
            ) in records
        )
