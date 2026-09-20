from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Tuple

from yoma.office.action_planning import ActionPlan
from yoma.office.decision_dependencies import DecisionDependencyMap


@dataclass(frozen=True)
class OrchestrationStep:
    """
    One explicitly ordered control-orchestration step.

    This model describes orchestration only. It does not execute anything.
    """

    step_id: str
    sequence: int
    plan_id: str
    action_type: str
    description: str
    target_user_id: Optional[str] = None
    target_system_id: Optional[str] = None
    dependency_ids: Tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("step_id is required")
        if not self.step_id.startswith("OSTEP-"):
            raise ValueError("step_id must start with OSTEP-")
        if not self.plan_id:
            raise ValueError("plan_id is required")
        if self.sequence < 1:
            raise ValueError("sequence must be >= 1")
        if not self.action_type:
            raise ValueError("action_type is required")
        if not self.requires_human_approval:
            raise ValueError("orchestration steps require human approval")
        if self.executable:
            raise ValueError("orchestration steps are not executable")


@dataclass(frozen=True)
class ControlOrchestration:
    """
    Immutable orchestration definition for an ActionPlan.

    The orchestration contains ordered control steps and explicit dependency
    references. It does not perform execution.
    """

    orchestration_id: str
    plan_id: str
    decision_id: str
    created_at: datetime
    steps: Tuple[OrchestrationStep, ...] = ()
    dependency_map_id: Optional[str] = None
    affected_user_ids: Tuple[str, ...] = ()
    affected_system_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.orchestration_id:
            raise ValueError("orchestration_id is required")
        if not self.orchestration_id.startswith("ORCH-"):
            raise ValueError("orchestration_id must start with ORCH-")
        if not self.plan_id:
            raise ValueError("plan_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.requires_human_approval:
            raise ValueError("orchestration requires human approval")
        if self.executable:
            raise ValueError("orchestration is not executable")

        sequences = tuple(step.sequence for step in self.steps)
        if sequences != tuple(sorted(sequences)):
            raise ValueError("orchestration steps must be ordered by sequence")

        if len(set(sequences)) != len(sequences):
            raise ValueError("orchestration step sequences must be unique")

        for step in self.steps:
            if step.plan_id != self.plan_id:
                raise ValueError("all orchestration steps must belong to the plan")

            if not step.requires_human_approval:
                raise ValueError(
                    "all orchestration steps require human approval"
                )

            if step.executable:
                raise ValueError(
                    "orchestration steps cannot be executable"
                )

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def first_step(self) -> Optional[OrchestrationStep]:
        return self.steps[0] if self.steps else None

    @property
    def last_step(self) -> Optional[OrchestrationStep]:
        return self.steps[-1] if self.steps else None

    @property
    def action_types(self) -> Tuple[str, ...]:
        return tuple(step.action_type for step in self.steps)

    @property
    def dependency_ids(self) -> Tuple[str, ...]:
        values = {
            dependency_id
            for step in self.steps
            for dependency_id in step.dependency_ids
        }
        return tuple(sorted(values))


class ControlOrchestrationEngine:
    """
    Builds deterministic orchestration models from existing ActionPlans and
    DecisionDependencyMaps.

    This engine only constructs orchestration metadata.
    It never executes actions.
    """

    def __init__(self) -> None:
        self._orchestrations: dict[str, ControlOrchestration] = {}

    @property
    def orchestrations(self) -> Tuple[ControlOrchestration, ...]:
        return tuple(self._orchestrations.values())

    def get(self, orchestration_id: str) -> Optional[ControlOrchestration]:
        return self._orchestrations.get(orchestration_id)

    def build(
        self,
        plan: ActionPlan,
        dependency_map: Optional[DecisionDependencyMap] = None,
    ) -> ControlOrchestration:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        if dependency_map is not None:
            if not isinstance(dependency_map, DecisionDependencyMap):
                raise TypeError(
                    "dependency_map must be a DecisionDependencyMap"
                )

            if dependency_map.plan_id != plan.plan_id:
                raise ValueError(
                    "dependency map plan_id must match action plan"
                )

            if dependency_map.decision_id != plan.decision_id:
                raise ValueError(
                    "dependency map decision_id must match action plan"
                )

        orchestration_id = f"ORCH-{plan.plan_id}"

        if orchestration_id in self._orchestrations:
            return self._orchestrations[orchestration_id]

        dependency_lookup = {}
        if dependency_map is not None:
            for dependency in dependency_map.dependencies:
                dependency_lookup.setdefault(
                    dependency.entity_id,
                    []
                ).append(dependency.dependency_id)

        steps = []

        for index, action_step in enumerate(plan.steps, start=1):
            dependency_ids = set()

            for entity_id in (
                action_step.target_user_id,
                action_step.target_system_id,
            ):
                if entity_id:
                    dependency_ids.update(
                        dependency_lookup.get(entity_id, ())
                    )

            step = OrchestrationStep(
                step_id=f"OSTEP-{plan.plan_id}-{index}",
                sequence=index,
                plan_id=plan.plan_id,
                action_type=action_step.action_type,
                description=action_step.description,
                target_user_id=action_step.target_user_id,
                target_system_id=action_step.target_system_id,
                dependency_ids=tuple(sorted(dependency_ids)),
                parameters=dict(action_step.parameters),
                requires_human_approval=True,
                executable=False,
            )

            steps.append(step)

        orchestration = ControlOrchestration(
            orchestration_id=orchestration_id,
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            created_at=plan.created_at,
            steps=tuple(steps),
            dependency_map_id=(
                dependency_map.dependency_map_id
                if dependency_map is not None
                else None
            ),
            affected_user_ids=tuple(sorted(plan.affected_user_ids)),
            affected_system_ids=tuple(sorted(plan.affected_system_ids)),
            requires_human_approval=True,
            executable=False,
            metadata={
                "decision_type": plan.decision_type,
                "priority": plan.priority,
                "reason": plan.reason,
                "dependency_depth": (
                    dependency_map.dependency_depth
                    if dependency_map is not None
                    else 0
                ),
            },
        )

        self._orchestrations[orchestration_id] = orchestration
        return orchestration

    def build_many(
        self,
        plans: Iterable[ActionPlan],
        dependency_maps: Iterable[DecisionDependencyMap] = (),
    ) -> Tuple[ControlOrchestration, ...]:
        dependency_lookup = {
            dependency_map.plan_id: dependency_map
            for dependency_map in dependency_maps
        }

        results = []

        for plan in plans:
            results.append(
                self.build(
                    plan,
                    dependency_lookup.get(plan.plan_id),
                )
            )

        return tuple(results)
