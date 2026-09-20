from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .action_planning import ActionPlan
from .action_execution import ExecutionResult
from .action_approval import ActionApprovalWorkflow


@dataclass(frozen=True)
class SandboxExecution:
    """
    Immutable record of a simulated execution.

    A sandbox execution is never a real execution and must never be
    treated as evidence that an external action actually occurred.
    """

    sandbox_id: str
    action_id: str
    action_type: str
    executor_name: str
    status: str
    created_at: datetime
    completed_at: datetime
    parameters: Mapping[str, Any] = field(default_factory=dict)
    simulated_output: Mapping[str, Any] = field(default_factory=dict)
    approval_id: str = ""
    workflow_id: str = ""
    plan_id: str = ""
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.sandbox_id.startswith("SANDBOX-"):
            raise ValueError("sandbox_id must start with SANDBOX-")

        if not self.action_id:
            raise ValueError("action_id is required")

        if not self.action_type:
            raise ValueError("action_type is required")

        if not self.executor_name:
            raise ValueError("executor_name is required")

        if self.status not in {
            "simulated",
            "rejected",
        }:
            raise ValueError(f"invalid sandbox status: {self.status}")

        if not self.requires_human_approval:
            raise ValueError(
                "sandbox execution must require human approval"
            )

        if self.executable:
            raise ValueError(
                "sandbox execution must never be executable"
            )


@dataclass(frozen=True)
class SandboxResult:
    """
    Result returned by the dry-run boundary.

    This deliberately resembles ExecutionResult enough for callers to
    reason about the proposed execution while remaining clearly separate
    from real execution.
    """

    sandbox_execution: SandboxExecution
    execution_result: ExecutionResult

    @property
    def sandbox_id(self) -> str:
        return self.sandbox_execution.sandbox_id

    @property
    def simulated(self) -> bool:
        return True

    @property
    def requires_human_approval(self) -> bool:
        return True

    @property
    def executable(self) -> bool:
        return False


class ExecutionSandbox:
    """
    Safe dry-run execution boundary.

    Security/governance invariants:

    1. An approved workflow is mandatory.
    2. The ActionPlan must match the workflow.
    3. No registered executor is ever invoked.
    4. No ActionExecutionGateway is required.
    5. No EXEC-* execution record is created.
    6. Sandbox output is explicitly marked simulated.
    7. Sandbox results remain non-executable.
    """

    def __init__(self) -> None:
        self._records: dict[str, SandboxExecution] = {}

    @property
    def records(self) -> tuple[SandboxExecution, ...]:
        return tuple(
            self._records[key]
            for key in sorted(self._records)
        )

    def get_record(
        self,
        sandbox_id: str,
    ) -> SandboxExecution | None:
        return self._records.get(sandbox_id)

    @staticmethod
    def _approval_details(
        workflow: ActionApprovalWorkflow,
    ) -> str:
        if workflow.status != "approved":
            raise PermissionError(
                "sandbox execution requires an approved workflow"
            )

        if not workflow.approval_history:
            raise PermissionError(
                "approved workflow has no approval record"
            )

        approval = workflow.approval_history[-1]

        if not approval.approval_id:
            raise PermissionError(
                "approved workflow has no approval id"
            )

        return approval.approval_id

    @staticmethod
    def _action_details(
        plan: ActionPlan,
    ) -> tuple[str, str, Mapping[str, Any]]:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if not plan.steps:
            raise ValueError(
                "action plan must contain at least one step"
            )

        step = plan.steps[0]

        action_id = getattr(step, "action_id", None) or step.step_id
        action_type = getattr(step, "action_type", None)

        if not action_id:
            raise ValueError("action step has no action id")

        if not action_type:
            raise ValueError("action step has no action type")

        parameters = getattr(step, "parameters", {}) or {}

        if not isinstance(parameters, Mapping):
            raise TypeError(
                "action step parameters must be a mapping"
            )

        return action_id, action_type, dict(parameters)

    def simulate(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        executor_name: str,
        created_at: datetime,
    ) -> SandboxResult:
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

        if not executor_name:
            raise ValueError("executor name is required")

        if workflow.plan_id != plan.plan_id:
            raise ValueError(
                "workflow plan_id does not match action plan"
            )

        if workflow.decision_id != plan.decision_id:
            raise ValueError(
                "workflow decision_id does not match action plan"
            )

        approval_id = self._approval_details(workflow)

        action_id, action_type, parameters = self._action_details(
            plan
        )

        sandbox_id = (
            f"SANDBOX-{workflow.workflow_id}-{action_id}"
        )

        if sandbox_id in self._records:
            raise ValueError(
                f"sandbox execution already exists: {sandbox_id}"
            )

        simulated_output = {
            "simulated": True,
            "dry_run": True,
            "action_id": action_id,
            "action_type": action_type,
            "executor": executor_name,
            "parameters": dict(parameters),
            "side_effects": False,
            "external_system_called": False,
            "human_approval_verified": True,
        }

        record = SandboxExecution(
            sandbox_id=sandbox_id,
            action_id=action_id,
            action_type=action_type,
            executor_name=executor_name,
            status="simulated",
            created_at=created_at,
            completed_at=created_at,
            parameters=dict(parameters),
            simulated_output=simulated_output,
            approval_id=approval_id,
            workflow_id=workflow.workflow_id,
            plan_id=plan.plan_id,
            requires_human_approval=True,
            executable=False,
        )

        self._records[sandbox_id] = record

        execution_result = ExecutionResult(
            execution_id=f"EXEC-SANDBOX-{action_id}",
            action_id=action_id,
            status="succeeded",
            started_at=created_at,
            completed_at=created_at,
            output=simulated_output,
            requires_human_approval=True,
            executable=False,
        )

        return SandboxResult(
            sandbox_execution=record,
            execution_result=execution_result,
        )

    def dry_run(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        executor_name: str,
        created_at: datetime,
    ) -> SandboxResult:
        return self.simulate(
            workflow=workflow,
            plan=plan,
            executor_name=executor_name,
            created_at=created_at,
        )
