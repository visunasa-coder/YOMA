from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from yoma.office.action_planning import ActionPlan
from yoma.office.action_simulation import ActionSimulation


@dataclass(frozen=True)
class WhatIfAlternative:
    alternative_id: str
    plan_id: str
    simulation_id: str
    expected_outcome_score: float
    risk_score: float
    confidence_score: float
    impact_score: float
    overall_score: float
    recommendation: str
    evidence_ids: Tuple[str, ...] = ()
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.alternative_id.startswith("WALT-"):
            raise ValueError("alternative_id must start with WALT-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.simulation_id.startswith("SIM-"):
            raise ValueError("simulation_id must start with SIM-")

        for name, value in (
            ("expected_outcome_score", self.expected_outcome_score),
            ("risk_score", self.risk_score),
            ("confidence_score", self.confidence_score),
            ("impact_score", self.impact_score),
            ("overall_score", self.overall_score),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

        if not self.recommendation:
            raise ValueError("recommendation must not be empty")


@dataclass(frozen=True)
class WhatIfComparison:
    comparison_id: str
    decision_id: str
    alternatives: Tuple[WhatIfAlternative, ...] = ()
    preferred_alternative_id: Optional[str] = None
    comparison_reason: str = ""
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.comparison_id.startswith("WIF-"):
            raise ValueError("comparison_id must start with WIF-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if not self.requires_human_approval:
            raise ValueError("what-if comparisons require human approval")

        ids = {alternative.alternative_id for alternative in self.alternatives}

        if self.preferred_alternative_id is not None:
            if self.preferred_alternative_id not in ids:
                raise ValueError(
                    "preferred_alternative_id must reference an alternative"
                )

    @property
    def alternative_count(self) -> int:
        return len(self.alternatives)

    @property
    def has_preference(self) -> bool:
        return self.preferred_alternative_id is not None

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def executable(self) -> bool:
        return False


class WhatIfIntelligenceEngine:
    """
    Compares simulated ActionPlans without executing or selecting
    an action autonomously.
    """

    def compare(
        self,
        decision_id: str,
        plans: Tuple[ActionPlan, ...] | list[ActionPlan],
        simulations: Tuple[ActionSimulation, ...] | list[ActionSimulation],
    ) -> WhatIfComparison:
        if not decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")

        plans = tuple(plans)
        simulations = tuple(simulations)

        if not plans:
            raise ValueError("at least one action plan is required")

        if len(plans) != len(simulations):
            raise ValueError("plans and simulations must have equal length")

        alternatives = tuple(
            self._build_alternative(plan, simulation)
            for plan, simulation in zip(plans, simulations)
        )

        ranked = sorted(
            alternatives,
            key=lambda item: (-item.overall_score, item.alternative_id),
        )

        preferred = ranked[0].alternative_id if ranked else None

        return WhatIfComparison(
            comparison_id=f"WIF-{decision_id}",
            decision_id=decision_id,
            alternatives=tuple(ranked),
            preferred_alternative_id=preferred,
            comparison_reason=(
                "Alternatives are ranked using simulated outcome, "
                "risk, confidence, and impact scores. The ranking is "
                "advisory and requires human review."
            ),
            requires_human_approval=True,
            metadata={
                "alternative_count": len(alternatives),
                "ranking_method": "deterministic_weighted_score",
            },
        )

    def _build_alternative(
        self,
        plan: ActionPlan,
        simulation: ActionSimulation,
    ) -> WhatIfAlternative:
        if simulation.plan_id != plan.plan_id:
            raise ValueError(
                "simulation must correspond to the supplied action plan"
            )

        if simulation.decision_id != plan.decision_id:
            raise ValueError(
                "simulation and plan must reference the same decision"
            )

        outcome_score = self._outcome_score(simulation)
        risk_score = self._risk_score(simulation)
        confidence = simulation.confidence
        impact_score = self._impact_score(plan)

        overall = round(
            (
                outcome_score * 0.35
                + (1.0 - risk_score) * 0.25
                + confidence * 0.20
                + impact_score * 0.20
            ),
            6,
        )

        return WhatIfAlternative(
            alternative_id=f"WALT-{plan.plan_id}",
            plan_id=plan.plan_id,
            simulation_id=simulation.simulation_id,
            expected_outcome_score=outcome_score,
            risk_score=risk_score,
            confidence_score=confidence,
            impact_score=impact_score,
            overall_score=overall,
            recommendation=(
                "This alternative has a stronger simulated profile, "
                "but requires human evaluation before approval."
            ),
            evidence_ids=simulation.evidence_ids,
            data={
                "step_count": plan.step_count,
                "outcome_count": simulation.outcome_count,
                "risk_count": simulation.risk_count,
                "priority": plan.priority,
            },
        )

    def _outcome_score(self, simulation: ActionSimulation) -> float:
        if not simulation.outcomes:
            return 0.0

        return round(
            sum(
                outcome.probability * outcome.confidence
                for outcome in simulation.outcomes
            )
            / len(simulation.outcomes),
            6,
        )

    def _risk_score(self, simulation: ActionSimulation) -> float:
        if not simulation.risks:
            return 0.0

        severity_weight = {
            "info": 0.10,
            "warning": 0.35,
            "high": 0.70,
            "critical": 1.00,
        }

        return round(
            sum(
                risk.probability * severity_weight[risk.severity]
                for risk in simulation.risks
            )
            / len(simulation.risks),
            6,
        )

    def _impact_score(self, plan: ActionPlan) -> float:
        entity_count = (
            len(plan.affected_user_ids)
            + len(plan.affected_system_ids)
        )

        return round(
            min(1.0, 0.30 + entity_count * 0.10),
            6,
        )

    def compare_simulations(
        self,
        decision_id: str,
        simulations: Tuple[ActionSimulation, ...] | list[ActionSimulation],
    ) -> WhatIfComparison:
        simulations = tuple(simulations)

        if not simulations:
            raise ValueError("at least one simulation is required")

        plans = tuple(
            self._plan_from_simulation_placeholder(simulation)
            for simulation in simulations
        )

        return self.compare(decision_id, plans, simulations)

    def _plan_from_simulation_placeholder(
        self,
        simulation: ActionSimulation,
    ) -> ActionPlan:
        raise ValueError(
            "compare_simulations requires original ActionPlan objects; "
            "use compare(decision_id, plans, simulations)"
        )
