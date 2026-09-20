from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional, Tuple

from yoma.office.multi_action_execution import MultiAction, MultiActionExecutionPlan
from yoma.office.dependency_aware_execution import ExecutionOrder


VALID_TRANSACTION_STATUSES = {
    "planned",
    "committed",
    "failed",
    "rollback_required",
    "rolled_back",
}


@dataclass(frozen=True)
class RollbackAction:
    rollback_id: str
    source_action_id: str
    sequence: int
    action_type: str
    description: str
    target_user_id: Optional[str] = None
    target_system_id: Optional[str] = None
    parameters: Mapping[str, object] = field(default_factory=dict)
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.rollback_id.startswith("RBAC-"):
            raise ValueError("rollback_id must start with RBAC-")
        if not self.source_action_id:
            raise ValueError("source_action_id is required")
        if self.sequence < 1:
            raise ValueError("sequence must be >= 1")
        if not self.action_type:
            raise ValueError("action_type is required")
        if not self.requires_human_approval:
            raise ValueError("rollback actions require human approval")
        if self.executable:
            raise ValueError("rollback actions are not executable")


@dataclass(frozen=True)
class TransactionBoundary:
    boundary_id: str
    execution_plan_id: str
    action_ids: Tuple[str, ...] = ()
    atomic: bool = True
    rollback_supported: bool = True
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.boundary_id.startswith("TXB-"):
            raise ValueError("boundary_id must start with TXB-")
        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")
        if not self.action_ids:
            raise ValueError("transaction boundary requires actions")
        if not self.requires_human_approval:
            raise ValueError("transaction boundaries require human approval")
        if self.executable:
            raise ValueError("transaction boundaries are not executable")


@dataclass(frozen=True)
class TransactionRollbackPlan:
    rollback_plan_id: str
    execution_plan_id: str
    transaction_boundary_id: str
    failed_action_id: Optional[str] = None
    committed_action_ids: Tuple[str, ...] = ()
    rollback_actions: Tuple[RollbackAction, ...] = ()
    status: str = "planned"
    rollback_required: bool = False
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.rollback_plan_id.startswith("RBPLAN-"):
            raise ValueError("rollback_plan_id must start with RBPLAN-")
        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")
        if not self.transaction_boundary_id:
            raise ValueError("transaction_boundary_id is required")
        if self.status not in VALID_TRANSACTION_STATUSES:
            raise ValueError("invalid transaction status")
        if not self.requires_human_approval:
            raise ValueError("rollback planning requires human approval")
        if self.executable:
            raise ValueError("rollback plans are not executable")

    @property
    def rollback_count(self) -> int:
        return len(self.rollback_actions)

    @property
    def requires_review(self) -> bool:
        return self.rollback_required or self.status in {
            "failed",
            "rollback_required",
        }


@dataclass(frozen=True)
class TransactionIntelligence:
    transaction_id: str
    execution_plan_id: str
    boundary: TransactionBoundary
    rollback_plan: TransactionRollbackPlan
    ordered_action_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.transaction_id.startswith("TX-"):
            raise ValueError("transaction_id must start with TX-")
        if not self.requires_human_approval:
            raise ValueError("transaction intelligence requires human approval")
        if self.executable:
            raise ValueError("transaction intelligence is not executable")

    @property
    def rollback_required(self) -> bool:
        return self.rollback_plan.rollback_required


class TransactionRollbackIntelligenceEngine:
    """
    Builds transaction boundaries and compensating rollback plans.

    This engine plans transaction behavior only.
    It never commits, rolls back, or executes an action.
    """

    def __init__(self) -> None:
        self._transactions: dict[str, TransactionIntelligence] = {}

    @property
    def transactions(self) -> Tuple[TransactionIntelligence, ...]:
        return tuple(self._transactions.values())

    def build(
        self,
        execution_plan: MultiActionExecutionPlan,
        execution_order: Optional[ExecutionOrder] = None,
    ) -> TransactionIntelligence:
        if not isinstance(execution_plan, MultiActionExecutionPlan):
            raise TypeError(
                "execution_plan must be a MultiActionExecutionPlan"
            )

        if execution_order is not None:
            if not isinstance(execution_order, ExecutionOrder):
                raise TypeError(
                    "execution_order must be an ExecutionOrder"
                )
            if execution_order.execution_plan_id != execution_plan.execution_plan_id:
                raise ValueError(
                    "execution order must belong to the execution plan"
                )

        transaction_id = f"TX-{execution_plan.execution_plan_id}"

        existing = self._transactions.get(transaction_id)
        if existing is not None:
            return existing

        action_ids = (
            execution_order.ordered_action_ids
            if execution_order is not None
            else tuple(action.action_id for action in execution_plan.actions)
        )

        boundary = TransactionBoundary(
            boundary_id=f"TXB-{execution_plan.execution_plan_id}",
            execution_plan_id=execution_plan.execution_plan_id,
            action_ids=tuple(action_ids),
            atomic=True,
            rollback_supported=True,
            requires_human_approval=True,
            executable=False,
        )

        rollback_plan = TransactionRollbackPlan(
            rollback_plan_id=f"RBPLAN-{execution_plan.execution_plan_id}",
            execution_plan_id=execution_plan.execution_plan_id,
            transaction_boundary_id=boundary.boundary_id,
            failed_action_id=None,
            committed_action_ids=(),
            rollback_actions=(),
            status="planned",
            rollback_required=False,
            requires_human_approval=True,
            executable=False,
        )

        result = TransactionIntelligence(
            transaction_id=transaction_id,
            execution_plan_id=execution_plan.execution_plan_id,
            boundary=boundary,
            rollback_plan=rollback_plan,
            ordered_action_ids=tuple(action_ids),
            requires_human_approval=True,
            executable=False,
        )

        self._transactions[transaction_id] = result
        return result

    def plan_rollback(
        self,
        execution_plan: MultiActionExecutionPlan,
        failed_action_id: str,
        committed_action_ids: Iterable[str],
    ) -> TransactionRollbackPlan:
        if not isinstance(execution_plan, MultiActionExecutionPlan):
            raise TypeError(
                "execution_plan must be a MultiActionExecutionPlan"
            )

        action_lookup = {
            action.action_id: action
            for action in execution_plan.actions
        }

        if failed_action_id not in action_lookup:
            raise ValueError("failed_action_id is not in execution plan")

        committed = tuple(committed_action_ids)

        for action_id in committed:
            if action_id not in action_lookup:
                raise ValueError(
                    f"committed action {action_id} is not in execution plan"
                )

        rollback_actions = []

        for index, action_id in enumerate(
            reversed(committed),
            start=1,
        ):
            action = action_lookup[action_id]

            rollback_actions.append(
                RollbackAction(
                    rollback_id=f"RBAC-{execution_plan.execution_plan_id}-{index}",
                    source_action_id=action.action_id,
                    sequence=index,
                    action_type=f"rollback.{action.action_type}",
                    description=f"Compensate action: {action.description}",
                    target_user_id=action.target_user_id,
                    target_system_id=action.target_system_id,
                    parameters={
                        "source_action_id": action.action_id,
                        "compensating": True,
                    },
                    requires_human_approval=True,
                    executable=False,
                )
            )

        return TransactionRollbackPlan(
            rollback_plan_id=f"RBPLAN-{execution_plan.execution_plan_id}-{failed_action_id}",
            execution_plan_id=execution_plan.execution_plan_id,
            transaction_boundary_id=f"TXB-{execution_plan.execution_plan_id}",
            failed_action_id=failed_action_id,
            committed_action_ids=committed,
            rollback_actions=tuple(rollback_actions),
            status="rollback_required" if committed else "failed",
            rollback_required=bool(committed),
            requires_human_approval=True,
            executable=False,
        )

    def get(
        self,
        transaction_id: str,
    ) -> Optional[TransactionIntelligence]:
        return self._transactions.get(transaction_id)
