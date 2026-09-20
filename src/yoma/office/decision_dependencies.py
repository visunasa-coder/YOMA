from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from yoma.office.action_planning import ActionPlan


@dataclass(frozen=True)
class DecisionDependency:
    dependency_id: str
    dependency_type: str
    entity_id: str
    relationship: str
    reason: str
    direct: bool = True
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dependency_id.startswith("DEP-"):
            raise ValueError("dependency_id must start with DEP-")
        if not self.dependency_type:
            raise ValueError("dependency_type must not be empty")
        if not self.entity_id:
            raise ValueError("entity_id must not be empty")
        if not self.relationship:
            raise ValueError("relationship must not be empty")
        if not self.reason:
            raise ValueError("reason must not be empty")


@dataclass(frozen=True)
class DecisionDependencyMap:
    dependency_map_id: str
    plan_id: str
    decision_id: str
    dependencies: Tuple[DecisionDependency, ...] = ()
    affected_user_ids: Tuple[str, ...] = ()
    affected_system_ids: Tuple[str, ...] = ()
    dependency_depth: int = 0
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dependency_map_id.startswith("DMAP-"):
            raise ValueError("dependency_map_id must start with DMAP-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if self.dependency_depth < 0:
            raise ValueError("dependency_depth must be >= 0")
        if not self.requires_human_approval:
            raise ValueError("dependency analysis requires human approval")

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)

    @property
    def user_dependency_count(self) -> int:
        return sum(
            dependency.dependency_type == "user"
            for dependency in self.dependencies
        )

    @property
    def system_dependency_count(self) -> int:
        return sum(
            dependency.dependency_type == "system"
            for dependency in self.dependencies
        )

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def executable(self) -> bool:
        return False


class DecisionDependencyEngine:
    """
    Builds an explicit dependency map for an ActionPlan.

    Dependencies are derived only from entities already explicitly
    present in the action plan. No free-text inference is performed.
    """

    def analyze(self, plan: ActionPlan) -> DecisionDependencyMap:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        dependencies = []

        for user_id in plan.affected_user_ids:
            dependencies.append(
                DecisionDependency(
                    dependency_id=f"DEP-{plan.plan_id}-USER-{user_id}",
                    dependency_type="user",
                    entity_id=user_id,
                    relationship="affected_user",
                    reason=(
                        "The proposed action directly affects this user."
                    ),
                    direct=True,
                    data={
                        "plan_id": plan.plan_id,
                    },
                )
            )

        for system_id in plan.affected_system_ids:
            dependencies.append(
                DecisionDependency(
                    dependency_id=f"DEP-{plan.plan_id}-SYSTEM-{system_id}",
                    dependency_type="system",
                    entity_id=system_id,
                    relationship="affected_system",
                    reason=(
                        "The proposed action directly affects this system."
                    ),
                    direct=True,
                    data={
                        "plan_id": plan.plan_id,
                    },
                )
            )

        for step in plan.steps:
            if step.target_user_id:
                dependency_id = (
                    f"DEP-{plan.plan_id}-STEP-{step.sequence}"
                    f"-USER-{step.target_user_id}"
                )

                dependencies.append(
                    DecisionDependency(
                        dependency_id=dependency_id,
                        dependency_type="user",
                        entity_id=step.target_user_id,
                        relationship="action_step_target",
                        reason=(
                            "This user is an explicit target of an "
                            "action-plan step."
                        ),
                        direct=True,
                        data={
                            "step_id": step.step_id,
                            "action_type": step.action_type,
                        },
                    )
                )

            if step.target_system_id:
                dependency_id = (
                    f"DEP-{plan.plan_id}-STEP-{step.sequence}"
                    f"-SYSTEM-{step.target_system_id}"
                )

                dependencies.append(
                    DecisionDependency(
                        dependency_id=dependency_id,
                        dependency_type="system",
                        entity_id=step.target_system_id,
                        relationship="action_step_target",
                        reason=(
                            "This system is an explicit target of an "
                            "action-plan step."
                        ),
                        direct=True,
                        data={
                            "step_id": step.step_id,
                            "action_type": step.action_type,
                        },
                    )
                )

        deduplicated = {
            dependency.dependency_id: dependency
            for dependency in dependencies
        }

        ordered = tuple(
            sorted(
                deduplicated.values(),
                key=lambda dependency: (
                    dependency.dependency_type,
                    dependency.entity_id,
                    dependency.dependency_id,
                ),
            )
        )

        return DecisionDependencyMap(
            dependency_map_id=f"DMAP-{plan.plan_id}",
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            dependencies=ordered,
            affected_user_ids=tuple(sorted(set(plan.affected_user_ids))),
            affected_system_ids=tuple(sorted(set(plan.affected_system_ids))),
            dependency_depth=1 if ordered else 0,
            requires_human_approval=True,
            metadata={
                "step_count": plan.step_count,
                "dependency_count": len(ordered),
            },
        )

    def analyze_many(
        self,
        plans: Tuple[ActionPlan, ...] | list[ActionPlan],
    ) -> Tuple[DecisionDependencyMap, ...]:
        return tuple(self.analyze(plan) for plan in plans)
