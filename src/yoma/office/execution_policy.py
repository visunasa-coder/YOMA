from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from yoma.office.action_approval import ActionApprovalWorkflow
from yoma.office.action_execution import ExecutionResult
from yoma.office.action_planning import ActionPlan
from yoma.office.approval_execution_bridge import ApprovalExecutionBridge
from yoma.office.policy_constraints import (
    PolicyCheckResult,
    PolicyConstraintEngine,
)


@dataclass(frozen=True)
class ExecutionPolicyResult:
    """
    Result of policy enforcement immediately before execution.

    A policy-blocked action never reaches the execution gateway.
    """

    policy_check: PolicyCheckResult
    execution: ExecutionResult | None = None
    executed: bool = False
    blocked: bool = False
    requires_human_approval: bool = True
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.requires_human_approval:
            raise ValueError(
                "execution policy results must require human approval"
            )

        if self.blocked and self.executed:
            raise ValueError(
                "blocked execution cannot be marked executed"
            )

        if self.policy_check.status == "blocked" and not self.blocked:
            raise ValueError(
                "blocked policy check must produce blocked result"
            )

        if self.executed and self.execution is None:
            raise ValueError(
                "executed result requires an execution result"
            )


class ExecutionPolicyEnforcer:
    """
    M32.4 enforcement boundary.

    M31.4 evaluates policy constraints.
    M32.4 enforces the resulting decision before execution.

    Governance invariants:

    1. The ActionPlan must be evaluated by PolicyConstraintEngine.
    2. A blocked plan never reaches ApprovalExecutionBridge.
    3. An allowed plan still requires an approved workflow.
    4. The existing ApprovalExecutionBridge remains the approval boundary.
    5. No policy engine executes actions.
    6. Human approval remains mandatory.
    """

    def __init__(
        self,
        policy_engine: PolicyConstraintEngine,
        execution_bridge: ApprovalExecutionBridge,
    ) -> None:
        if not isinstance(
            policy_engine,
            PolicyConstraintEngine,
        ):
            raise TypeError(
                "policy_engine must be a PolicyConstraintEngine"
            )

        if not isinstance(
            execution_bridge,
            ApprovalExecutionBridge,
        ):
            raise TypeError(
                "execution_bridge must be an ApprovalExecutionBridge"
            )

        self._policy_engine = policy_engine
        self._execution_bridge = execution_bridge

    @property
    def policy_engine(self) -> PolicyConstraintEngine:
        return self._policy_engine

    @property
    def execution_bridge(self) -> ApprovalExecutionBridge:
        return self._execution_bridge

    def check(
        self,
        plan: ActionPlan,
    ) -> PolicyCheckResult:
        return self._policy_engine.evaluate(plan)

    def execute(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        executor_name: str,
        created_at: datetime,
    ) -> ExecutionPolicyResult:
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

        policy_check = self._policy_engine.evaluate(plan)

        if policy_check.blocked:
            reason = (
                "; ".join(policy_check.reasons)
                if policy_check.reasons
                else "execution blocked by policy"
            )

            return ExecutionPolicyResult(
                policy_check=policy_check,
                execution=None,
                executed=False,
                blocked=True,
                requires_human_approval=True,
                reason=reason,
                metadata={
                    "policy_status": policy_check.status,
                    "failed_constraint_count": (
                        policy_check.failed_count
                    ),
                },
            )

        governed = self._execution_bridge.execute_approved(
            workflow,
            plan,
            executor_name=executor_name,
            created_at=created_at,
        )

        return ExecutionPolicyResult(
            policy_check=policy_check,
            execution=governed.execution,
            executed=True,
            blocked=False,
            requires_human_approval=True,
            reason="execution allowed by policy",
            metadata={
                "policy_status": policy_check.status,
                "passed_constraint_count": (
                    policy_check.passed_count
                ),
                "workflow_id": governed.workflow_id,
                "approval_id": governed.approval_id,
            },
        )

    def execute_approved(
        self,
        *,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        executor_name: str,
        created_at: datetime,
    ) -> ExecutionPolicyResult:
        return self.execute(
            workflow=workflow,
            plan=plan,
            executor_name=executor_name,
            created_at=created_at,
        )
