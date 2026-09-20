"""M34.2 Unified Control Runtime.

Composes the existing M31 Control Intelligence runtime with the
M33.9 Unified Control Orchestration runtime.

This module is a composition layer only.

It does not:
- execute actions
- create a second approval system
- create a second policy engine
- bypass human approval
- replace M33.9 components
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from .action_planning import ActionPlan
from .control_intelligence import (
    ControlIntelligenceResult,
    ControlIntelligenceRuntime,
)
from .decision_intelligence import DecisionIntelligence
from .unified_control_orchestration import (
    UnifiedControlOrchestrationResult,
    UnifiedControlOrchestrationRuntime,
)


@dataclass(frozen=True)
class UnifiedControlRuntimeResult:
    """Unified M34.2 lifecycle result.

    M34.2 composes M31 intelligence/planning with M33.9
    orchestration. Execution remains outside this runtime.
    """

    control_intelligence: ControlIntelligenceResult
    orchestration: Tuple[
        UnifiedControlOrchestrationResult, ...
    ]
    selected_plan_index: int = 0
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        if not self.orchestration:
            raise ValueError(
                "orchestration result is required"
            )

        if not (
            0 <= self.selected_plan_index
            < len(self.control_intelligence.plans)
        ):
            raise IndexError(
                "selected_plan_index out of range"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "human approval must remain required"
            )

        if self.executable:
            raise ValueError(
                "M34.2 runtime cannot be executable"
            )

        if self.metadata is None:
            object.__setattr__(
                self,
                "metadata",
                {},
            )

    @property
    def selected_plan(self) -> ActionPlan:
        return self.control_intelligence.plans[
            self.selected_plan_index
        ]

    @property
    def selected_orchestration(
        self,
    ) -> UnifiedControlOrchestrationResult:
        return self.orchestration[
            self.selected_plan_index
        ]

    @property
    def decision_id(self) -> str:
        return self.control_intelligence.decision.decision_id

    @property
    def plan_id(self) -> str:
        return self.selected_plan.plan_id

    @property
    def orchestration_id(self) -> str:
        return self.selected_orchestration.orchestration_id

    @property
    def approval_pending(self) -> bool:
        return any(
            result.approval_pending_count > 0
            for result in self.orchestration
        )


class UnifiedControlRuntime:
    """M34.2 composition runtime.

    Pipeline:

        DecisionIntelligence
          -> M31 Control Intelligence
          -> ActionPlan
          -> M33.9 Unified Control Orchestration

    No action execution is performed.
    """

    def __init__(
        self,
        *,
        control_intelligence: Optional[
            ControlIntelligenceRuntime
        ] = None,
        orchestration_runtime: Optional[
            UnifiedControlOrchestrationRuntime
        ] = None,
    ) -> None:
        self.control_intelligence = (
            control_intelligence
            or ControlIntelligenceRuntime()
        )

        self.orchestration_runtime = (
            orchestration_runtime
            or UnifiedControlOrchestrationRuntime()
        )

        self._last_result: (
            UnifiedControlRuntimeResult | None
        ) = None

    @property
    def last_result(
        self,
    ) -> UnifiedControlRuntimeResult | None:
        return self._last_result

    def analyze(
        self,
        decision: DecisionIntelligence,
        *,
        scheduled_at: datetime,
        created_at: datetime,
        alternative_plans: Tuple[
            ActionPlan, ...
        ] = (),
        dependency_map: Any = None,
        metadata: Optional[
            Mapping[str, Any]
        ] = None,
        selected_plan_index: int = 0,
    ) -> UnifiedControlRuntimeResult:
        """Compose M31 planning with M33.9 orchestration."""

        if not isinstance(
            decision,
            DecisionIntelligence,
        ):
            raise TypeError(
                "decision must be a DecisionIntelligence"
            )

        if scheduled_at.tzinfo is None:
            raise ValueError(
                "scheduled_at must be timezone-aware"
            )

        if created_at.tzinfo is None:
            raise ValueError(
                "created_at must be timezone-aware"
            )

        control_result = (
            self.control_intelligence.analyze(
                decision,
                alternative_plans=alternative_plans
                or None,
            )
        )

        plans = control_result.plans

        if not 0 <= selected_plan_index < len(plans):
            raise IndexError(
                "selected_plan_index out of range"
            )

        orchestration_results = (
            self.orchestration_runtime.orchestrate_many(
                plans,
                scheduled_at=scheduled_at,
                created_at=created_at,
                dependency_map=dependency_map,
                metadata=metadata,
            )
        )

        result = UnifiedControlRuntimeResult(
            control_intelligence=control_result,
            orchestration=orchestration_results,
            selected_plan_index=selected_plan_index,
            requires_human_approval=True,
            executable=False,
            metadata=dict(metadata or {}),
        )

        self._last_result = result
        return result

    @property
    def executable(self) -> bool:
        """M34.2 never executes actions."""
        return False

    @property
    def requires_human_approval(self) -> bool:
        return True
