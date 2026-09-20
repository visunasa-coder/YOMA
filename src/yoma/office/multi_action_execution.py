from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Tuple

from yoma.office.control_orchestration import (
    ControlOrchestration,
    OrchestrationStep,
)


@dataclass(frozen=True)
class MultiAction:
    """
    One action participating in a coordinated execution plan.

    This is an orchestration description only. It never executes an action.
    """

    action_id: str
    sequence: int
    action_type: str
    description: str
    target_user_id: Optional[str] = None
    target_system_id: Optional[str] = None
    dependency_ids: Tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("action_id is required")
        if not self.action_id.startswith("MACT-"):
            raise ValueError("action_id must start with MACT-")
        if self.sequence < 1:
            raise ValueError("sequence must be >= 1")
        if not self.action_type:
            raise ValueError("action_type is required")
        if not self.requires_human_approval:
            raise ValueError("multi-actions require human approval")
        if self.executable:
            raise ValueError("multi-actions are not executable")


@dataclass(frozen=True)
class MultiActionExecutionPlan:
    """
    Coordinated collection of multiple actions.

    The plan describes what would be coordinated and in what order.
    Actual execution remains owned by M32 governed execution.
    """

    execution_plan_id: str
    orchestration_id: str
    plan_id: str
    decision_id: str
    created_at: datetime
    actions: Tuple[MultiAction, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.execution_plan_id:
            raise ValueError("execution_plan_id is required")
        if not self.execution_plan_id.startswith("MAPLAN-"):
            raise ValueError("execution_plan_id must start with MAPLAN-")
        if not self.orchestration_id:
            raise ValueError("orchestration_id is required")
        if not self.plan_id:
            raise ValueError("plan_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.requires_human_approval:
            raise ValueError("multi-action plans require human approval")
        if self.executable:
            raise ValueError("multi-action plans are not executable")

        sequences = tuple(action.sequence for action in self.actions)

        if sequences != tuple(sorted(sequences)):
            raise ValueError("actions must be ordered by sequence")

        if len(set(sequences)) != len(sequences):
            raise ValueError("action sequences must be unique")

        action_ids = tuple(action.action_id for action in self.actions)

        if len(set(action_ids)) != len(action_ids):
            raise ValueError("action IDs must be unique")

        for action in self.actions:
            if not action.requires_human_approval:
                raise ValueError(
                    "all multi-actions require human approval"
                )

            if action.executable:
                raise ValueError(
                    "multi-actions cannot be executable"
                )

    @property
    def action_count(self) -> int:
        return len(self.actions)

    @property
    def action_ids(self) -> Tuple[str, ...]:
        return tuple(action.action_id for action in self.actions)

    @property
    def action_types(self) -> Tuple[str, ...]:
        return tuple(action.action_type for action in self.actions)

    @property
    def first_action(self) -> Optional[MultiAction]:
        return self.actions[0] if self.actions else None

    @property
    def last_action(self) -> Optional[MultiAction]:
        return self.actions[-1] if self.actions else None

    @property
    def dependency_ids(self) -> Tuple[str, ...]:
        values = {
            dependency_id
            for action in self.actions
            for dependency_id in action.dependency_ids
        }
        return tuple(sorted(values))


class MultiActionExecutionPlanEngine:
    """
    Converts a M33.1 ControlOrchestration into a coordinated
    multi-action execution plan.

    No action is executed here.
    """

    def __init__(self) -> None:
        self._plans: dict[str, MultiActionExecutionPlan] = {}

    @property
    def plans(self) -> Tuple[MultiActionExecutionPlan, ...]:
        return tuple(self._plans.values())

    def get(
        self,
        execution_plan_id: str,
    ) -> Optional[MultiActionExecutionPlan]:
        return self._plans.get(execution_plan_id)

    def build(
        self,
        orchestration: ControlOrchestration,
    ) -> MultiActionExecutionPlan:
        if not isinstance(orchestration, ControlOrchestration):
            raise TypeError(
                "orchestration must be a ControlOrchestration"
            )

        execution_plan_id = f"MAPLAN-{orchestration.orchestration_id}"

        existing = self._plans.get(execution_plan_id)
        if existing is not None:
            return existing

        actions = tuple(
            MultiAction(
                action_id=f"MACT-{orchestration.plan_id}-{index}",
                sequence=index,
                action_type=step.action_type,
                description=step.description,
                target_user_id=step.target_user_id,
                target_system_id=step.target_system_id,
                dependency_ids=step.dependency_ids,
                parameters=dict(step.parameters),
                requires_human_approval=True,
                executable=False,
            )
            for index, step in enumerate(orchestration.steps, start=1)
        )

        result = MultiActionExecutionPlan(
            execution_plan_id=execution_plan_id,
            orchestration_id=orchestration.orchestration_id,
            plan_id=orchestration.plan_id,
            decision_id=orchestration.decision_id,
            created_at=orchestration.created_at,
            actions=actions,
            requires_human_approval=True,
            executable=False,
            metadata={
                "source": "m33.1_control_orchestration",
                "action_count": len(actions),
            },
        )

        self._plans[execution_plan_id] = result
        return result

    def build_many(
        self,
        orchestrations: Iterable[ControlOrchestration],
    ) -> Tuple[MultiActionExecutionPlan, ...]:
        return tuple(
            self.build(orchestration)
            for orchestration in orchestrations
        )
