from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from yoma.office.action_approval import (
    ActionApprovalEngine,
    ActionApprovalWorkflow,
)
from yoma.office.action_planning import (
    ActionPlan,
    ActionPlanningEngine,
)
from yoma.office.action_simulation import (
    ActionSimulation,
    ActionSimulationEngine,
)
from yoma.office.closed_loop_observation import (
    ClosedLoopObservation,
    ClosedLoopObservationEngine,
)
from yoma.office.decision_dependencies import (
    DecisionDependencyEngine,
    DecisionDependencyMap,
)
from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.outcome_learning import (
    OutcomeLearningEngine,
    OutcomeLearningResult,
)
from yoma.office.policy_constraints import (
    PolicyCheckResult,
    PolicyConstraint,
    PolicyConstraintEngine,
)
from yoma.office.what_if_intelligence import (
    WhatIfComparison,
    WhatIfIntelligenceEngine,
)


@dataclass(frozen=True)
class ControlIntelligenceResult:
    decision: DecisionIntelligence
    plans: Tuple[ActionPlan, ...]
    simulations: Tuple[ActionSimulation, ...]
    what_if: WhatIfComparison
    policy_checks: Tuple[PolicyCheckResult, ...]
    dependencies: Tuple[DecisionDependencyMap, ...]
    approval_workflows: Tuple[ActionApprovalWorkflow, ...]
    observations: Tuple[ClosedLoopObservation, ...]
    learning_results: Tuple[OutcomeLearningResult, ...]
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.requires_human_approval:
            raise ValueError(
                "control intelligence requires human approval"
            )

    @property
    def plan_count(self) -> int:
        return len(self.plans)

    @property
    def simulation_count(self) -> int:
        return len(self.simulations)

    @property
    def policy_check_count(self) -> int:
        return len(self.policy_checks)

    @property
    def dependency_map_count(self) -> int:
        return len(self.dependencies)

    @property
    def approval_count(self) -> int:
        return len(self.approval_workflows)

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def learning_count(self) -> int:
        return len(self.learning_results)

    @property
    def executable(self) -> bool:
        return False


class ControlIntelligenceRuntime:
    """
    M31 end-to-end orchestration layer.

    Existing M31 components remain the owners of their respective
    intelligence domains. This runtime only composes them.

    No action is executed by this runtime.
    """

    def __init__(
        self,
        *,
        planning_engine: ActionPlanningEngine | None = None,
        simulation_engine: ActionSimulationEngine | None = None,
        what_if_engine: WhatIfIntelligenceEngine | None = None,
        policy_engine: PolicyConstraintEngine | None = None,
        dependency_engine: DecisionDependencyEngine | None = None,
        approval_engine: ActionApprovalEngine | None = None,
        observation_engine: ClosedLoopObservationEngine | None = None,
        learning_engine: OutcomeLearningEngine | None = None,
    ) -> None:
        self._planning = planning_engine or ActionPlanningEngine()
        self._simulation = simulation_engine or ActionSimulationEngine()
        self._what_if = what_if_engine or WhatIfIntelligenceEngine()
        self._policy = policy_engine or PolicyConstraintEngine()
        self._dependencies = (
            dependency_engine or DecisionDependencyEngine()
        )
        self._approval = approval_engine or ActionApprovalEngine()
        self._observation = (
            observation_engine or ClosedLoopObservationEngine()
        )
        self._learning = learning_engine or OutcomeLearningEngine()

        self._last_result: ControlIntelligenceResult | None = None

    @property
    def last_result(self) -> ControlIntelligenceResult | None:
        return self._last_result

    def analyze(
        self,
        decision: DecisionIntelligence,
        *,
        alternative_plans: Tuple[ActionPlan, ...] | None = None,
    ) -> ControlIntelligenceResult:
        if not isinstance(decision, DecisionIntelligence):
            raise TypeError(
                "decision must be a DecisionIntelligence"
            )

        primary_plan = self._planning.build(decision)

        if alternative_plans:
            plans = (primary_plan, *tuple(alternative_plans))
        else:
            plans = (primary_plan,)

        for plan in plans:
            if plan.decision_id != decision.decision_id:
                raise ValueError(
                    "all plans must reference the same decision"
                )

        simulations = tuple(
            self._simulation.simulate(plan)
            for plan in plans
        )

        what_if = self._what_if.compare(
            decision.decision_id,
            plans,
            simulations,
        )

        policy_checks = tuple(
            self._policy.evaluate(plan)
            for plan in plans
        )

        dependencies = tuple(
            self._dependencies.analyze(plan)
            for plan in plans
        )

        approval_workflows = tuple(
            self._approval.create(plan)
            for plan in plans
        )

        result = ControlIntelligenceResult(
            decision=decision,
            plans=plans,
            simulations=simulations,
            what_if=what_if,
            policy_checks=policy_checks,
            dependencies=dependencies,
            approval_workflows=approval_workflows,
            observations=(),
            learning_results=(),
            requires_human_approval=True,
        )

        self._last_result = result
        return result

    def approve_plan(
        self,
        result: ControlIntelligenceResult,
        plan_index: int,
        reviewer_id: str,
        decided_at,
        comment: str = "",
    ) -> ControlIntelligenceResult:
        if not isinstance(result, ControlIntelligenceResult):
            raise TypeError(
                "result must be a ControlIntelligenceResult"
            )

        if not 0 <= plan_index < len(result.approval_workflows):
            raise IndexError("plan_index out of range")

        workflow = result.approval_workflows[plan_index]

        approved = self._approval.approve(
            workflow,
            reviewer_id=reviewer_id,
            decided_at=decided_at,
            comment=comment,
        )

        workflows = list(result.approval_workflows)
        workflows[plan_index] = approved

        updated = ControlIntelligenceResult(
            decision=result.decision,
            plans=result.plans,
            simulations=result.simulations,
            what_if=result.what_if,
            policy_checks=result.policy_checks,
            dependencies=result.dependencies,
            approval_workflows=tuple(workflows),
            observations=result.observations,
            learning_results=result.learning_results,
            requires_human_approval=True,
        )

        self._last_result = updated
        return updated

    def observe(
        self,
        result: ControlIntelligenceResult,
        plan_index: int,
        observed_at,
        outcome_status: str,
        description: str,
        event_ids: Tuple[str, ...] = (),
    ) -> ControlIntelligenceResult:
        if not isinstance(result, ControlIntelligenceResult):
            raise TypeError(
                "result must be a ControlIntelligenceResult"
            )

        if not 0 <= plan_index < len(result.approval_workflows):
            raise IndexError("plan_index out of range")

        workflow = result.approval_workflows[plan_index]

        loop = self._observation.create(workflow)

        updated_loop = self._observation.record(
            loop,
            observed_at=observed_at,
            outcome_status=outcome_status,
            description=description,
            event_ids=event_ids,
        )

        observations = list(result.observations)
        observations.append(updated_loop)

        updated = ControlIntelligenceResult(
            decision=result.decision,
            plans=result.plans,
            simulations=result.simulations,
            what_if=result.what_if,
            policy_checks=result.policy_checks,
            dependencies=result.dependencies,
            approval_workflows=result.approval_workflows,
            observations=tuple(observations),
            learning_results=result.learning_results,
            requires_human_approval=True,
        )

        self._last_result = updated
        return updated

    def learn(
        self,
        result: ControlIntelligenceResult,
        plan_index: int,
    ) -> ControlIntelligenceResult:
        if not isinstance(result, ControlIntelligenceResult):
            raise TypeError(
                "result must be a ControlIntelligenceResult"
            )

        if not 0 <= plan_index < len(result.simulations):
            raise IndexError("plan_index out of range")

        if not result.observations:
            raise ValueError(
                "an observation is required before learning"
            )

        simulation = result.simulations[plan_index]

        matching = [
            observation
            for observation in result.observations
            if observation.plan_id == simulation.plan_id
        ]

        if not matching:
            raise ValueError(
                "no observation exists for the selected plan"
            )

        learning = self._learning.learn(
            simulation,
            matching[-1],
        )

        updated = ControlIntelligenceResult(
            decision=result.decision,
            plans=result.plans,
            simulations=result.simulations,
            what_if=result.what_if,
            policy_checks=result.policy_checks,
            dependencies=result.dependencies,
            approval_workflows=result.approval_workflows,
            observations=result.observations,
            learning_results=(
                *result.learning_results,
                learning,
            ),
            requires_human_approval=True,
        )

        self._last_result = updated
        return updated
