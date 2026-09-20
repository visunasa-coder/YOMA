"""M33.9 Unified Control Orchestration Runtime.

Composes M33.1 through M33.8 into one human-governed
control orchestration pipeline.

This runtime NEVER executes actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from .action_planning import ActionPlan
from .decision_dependencies import DecisionDependencyMap
from .control_orchestration import (
    ControlOrchestration,
    ControlOrchestrationEngine,
)
from .multi_action_execution import (
    MultiActionExecutionPlan,
    MultiActionExecutionPlanEngine,
)
from .dependency_aware_execution import (
    DependencyExecutionAnalysis,
    DependencyAwareExecutionEngine,
    ExecutionOrder,
)
from .transaction_rollback import (
    TransactionIntelligence,
    TransactionRollbackIntelligenceEngine,
)
from .execution_scheduling import (
    ExecutionSchedule,
    ExecutionSchedulingEngine,
)
from .human_approval_queue import (
    ApprovalQueueItem,
    HumanApprovalQueueEngine,
)
from .cross_system_coordination import (
    CrossSystemCoordination,
    CrossSystemCoordinationEngine,
)
from .orchestration_intelligence import (
    OrchestrationIntelligence,
    OrchestrationIntelligenceEngine,
)


@dataclass(frozen=True)
class UnifiedControlOrchestrationResult:
    """Unified result produced by the complete M33 pipeline."""

    orchestration: ControlOrchestration
    execution_plan: MultiActionExecutionPlan
    execution_order: ExecutionOrder
    dependency_analysis: DependencyExecutionAnalysis
    transaction: TransactionIntelligence
    schedule: ExecutionSchedule
    approval_items: Tuple[ApprovalQueueItem, ...]
    coordination: CrossSystemCoordination
    intelligence: OrchestrationIntelligence
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @property
    def orchestration_id(self) -> str:
        return self.orchestration.orchestration_id

    @property
    def execution_plan_id(self) -> str:
        return self.execution_plan.execution_plan_id

    @property
    def action_count(self) -> int:
        return len(self.execution_plan.actions)

    @property
    def approval_pending_count(self) -> int:
        return sum(
            1
            for item in self.approval_items
            if getattr(item, "status", None) == "pending"
        )

    @property
    def system_count(self) -> int:
        return len(
            self.coordination.participating_system_ids
        )

    @property
    def requires_review(self) -> bool:
        return bool(
            self.intelligence.health.status != "healthy"
            or self.intelligence.health.rollback_required
            or self.approval_pending_count > 0
            or self.dependency_analysis.blocked_action_ids
            or self.dependency_analysis.missing_dependency_ids
        )


class UnifiedControlOrchestrationRuntime:
    """Compose M33.1-M33.8 into one unified runtime.

    The runtime performs:

        ActionPlan
          -> Control Orchestration
          -> Multi-Action Execution Plan
          -> Dependency Ordering
          -> Transaction Intelligence
          -> Scheduling
          -> Human Approval Queue
          -> Cross-System Coordination
          -> Orchestration Intelligence

    No action execution is performed.
    """

    def __init__(
        self,
        *,
        orchestration_engine: Optional[
            ControlOrchestrationEngine
        ] = None,
        execution_plan_engine: Optional[
            MultiActionExecutionPlanEngine
        ] = None,
        dependency_engine: Optional[
            DependencyAwareExecutionEngine
        ] = None,
        transaction_engine: Optional[
            TransactionRollbackIntelligenceEngine
        ] = None,
        scheduling_engine: Optional[
            ExecutionSchedulingEngine
        ] = None,
        approval_queue: Optional[
            HumanApprovalQueueEngine
        ] = None,
        coordination_engine: Optional[
            CrossSystemCoordinationEngine
        ] = None,
        intelligence_engine: Optional[
            OrchestrationIntelligenceEngine
        ] = None,
    ) -> None:

        self.orchestration_engine = (
            orchestration_engine
            or ControlOrchestrationEngine()
        )

        self.execution_plan_engine = (
            execution_plan_engine
            or MultiActionExecutionPlanEngine()
        )

        self.dependency_engine = (
            dependency_engine
            or DependencyAwareExecutionEngine()
        )

        self.transaction_engine = (
            transaction_engine
            or TransactionRollbackIntelligenceEngine()
        )

        self.scheduling_engine = (
            scheduling_engine
            or ExecutionSchedulingEngine(
                dependency_engine=self.dependency_engine,
                transaction_engine=self.transaction_engine,
            )
        )

        self.approval_queue = (
            approval_queue
            or HumanApprovalQueueEngine()
        )

        self.coordination_engine = (
            coordination_engine
            or CrossSystemCoordinationEngine()
        )

        self.intelligence_engine = (
            intelligence_engine
            or OrchestrationIntelligenceEngine()
        )

        self._cache: dict[
            str,
            UnifiedControlOrchestrationResult,
        ] = {}

    def orchestrate(
        self,
        plan: ActionPlan,
        *,
        scheduled_at: datetime,
        created_at: datetime,
        dependency_map: Optional[
            DecisionDependencyMap
        ] = None,
        metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> UnifiedControlOrchestrationResult:

        if not isinstance(plan, ActionPlan):
            raise TypeError(
                "plan must be an ActionPlan"
            )

        if scheduled_at.tzinfo is None:
            raise ValueError(
                "scheduled_at must be timezone-aware"
            )

        if created_at.tzinfo is None:
            raise ValueError(
                "created_at must be timezone-aware"
            )

        orchestration = (
            self.orchestration_engine.build(
                plan,
                dependency_map=dependency_map,
            )
        )

        execution_plan = (
            self.execution_plan_engine.build(
                orchestration
            )
        )

        cache_key = (
            execution_plan.execution_plan_id
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        execution_order = (
            self.dependency_engine.order(
                execution_plan
            )
        )

        dependency_analysis = (
            self.dependency_engine.analyze(
                execution_plan
            )
        )

        scheduling_result = (
            self.scheduling_engine.schedule(
                execution_plan,
                scheduled_at=scheduled_at,
                created_at=created_at,
                metadata=metadata,
            )
        )

        schedule = scheduling_result.schedule
        transaction = scheduling_result.transaction

        approval_item = (
            self.approval_queue.enqueue(
                schedule,
                plan,
            )
        )

        coordination = (
            self.coordination_engine.coordinate(
                execution_plan
            )
        )

        intelligence = (
            self.intelligence_engine.analyze(
                execution_plan,
                execution_order,
                transaction,
                coordination,
                schedule,
                approval_items=(
                    approval_item,
                ),
            )
        )

        result = UnifiedControlOrchestrationResult(
            orchestration=orchestration,
            execution_plan=execution_plan,
            execution_order=execution_order,
            dependency_analysis=dependency_analysis,
            transaction=transaction,
            schedule=schedule,
            approval_items=(
                approval_item,
            ),
            coordination=coordination,
            intelligence=intelligence,
            requires_human_approval=True,
            executable=False,
            metadata=dict(
                metadata or {}
            ),
        )

        self._cache[cache_key] = result

        return result

    def orchestrate_many(
        self,
        plans: Tuple[ActionPlan, ...],
        *,
        scheduled_at: datetime,
        created_at: datetime,
        dependency_map: Optional[
            DecisionDependencyMap
        ] = None,
        metadata: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> Tuple[
        UnifiedControlOrchestrationResult, ...
    ]:

        return tuple(
            self.orchestrate(
                plan,
                scheduled_at=scheduled_at,
                created_at=created_at,
                dependency_map=dependency_map,
                metadata=metadata,
            )
            for plan in plans
        )

    def get(
        self,
        execution_plan_id: str,
    ) -> Optional[
        UnifiedControlOrchestrationResult
    ]:
        return self._cache.get(
            execution_plan_id
        )

    @property
    def results(
        self,
    ) -> Tuple[
        UnifiedControlOrchestrationResult, ...
    ]:
        return tuple(
            self._cache.values()
        )

    def clear(self) -> None:
        self._cache.clear()

    @property
    def executable(self) -> bool:
        """M33.9 cannot execute actions."""
        return False

    @property
    def requires_human_approval(self) -> bool:
        return True
