from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from yoma.office.action_planning import ActionPlan


@dataclass(frozen=True)
class SimulationOutcome:
    outcome_id: str
    outcome_type: str
    description: str
    probability: float
    confidence: float
    affected_user_ids: Tuple[str, ...] = ()
    affected_system_ids: Tuple[str, ...] = ()
    evidence_ids: Tuple[str, ...] = ()
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.outcome_id.startswith("SOUT-"):
            raise ValueError("outcome_id must start with SOUT-")
        if not self.outcome_type:
            raise ValueError("outcome_type must not be empty")
        if not self.description:
            raise ValueError("description must not be empty")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class SimulationRisk:
    risk_id: str
    risk_type: str
    description: str
    probability: float
    severity: str
    mitigation: str
    evidence_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.risk_id.startswith("SRISK-"):
            raise ValueError("risk_id must start with SRISK-")
        if not self.risk_type:
            raise ValueError("risk_type must not be empty")
        if not self.description:
            raise ValueError("description must not be empty")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        if self.severity not in {"info", "warning", "high", "critical"}:
            raise ValueError("invalid risk severity")
        if not self.mitigation:
            raise ValueError("mitigation must not be empty")


@dataclass(frozen=True)
class ActionSimulation:
    simulation_id: str
    plan_id: str
    decision_id: str
    outcomes: Tuple[SimulationOutcome, ...] = ()
    risks: Tuple[SimulationRisk, ...] = ()
    confidence: float = 0.0
    affected_user_ids: Tuple[str, ...] = ()
    affected_system_ids: Tuple[str, ...] = ()
    evidence_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.simulation_id.startswith("SIM-"):
            raise ValueError("simulation_id must start with SIM-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.requires_human_approval:
            raise ValueError("simulation must require human approval")

    @property
    def outcome_count(self) -> int:
        return len(self.outcomes)

    @property
    def risk_count(self) -> int:
        return len(self.risks)

    @property
    def high_risk(self) -> bool:
        return any(
            risk.severity in {"high", "critical"}
            for risk in self.risks
        )

    @property
    def executable(self) -> bool:
        return False


class ActionSimulationEngine:
    """
    Deterministic, advisory simulation of an ActionPlan.

    This engine never executes actions or contacts external systems.
    """

    def simulate(self, plan: ActionPlan) -> ActionSimulation:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        evidence_ids = tuple(
            evidence.evidence_id
            for evidence in plan.evidence
        )

        outcomes = self._build_outcomes(plan, evidence_ids)
        risks = self._build_risks(plan, evidence_ids)

        confidence = self._confidence(plan)

        return ActionSimulation(
            simulation_id=f"SIM-{plan.plan_id}",
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            outcomes=outcomes,
            risks=risks,
            confidence=confidence,
            affected_user_ids=plan.affected_user_ids,
            affected_system_ids=plan.affected_system_ids,
            evidence_ids=evidence_ids,
            requires_human_approval=True,
            metadata={
                "step_count": plan.step_count,
                "priority": plan.priority,
                "recommendation_type": plan.metadata.get(
                    "recommendation_type"
                ),
            },
        )

    def simulate_many(
        self,
        plans: tuple[ActionPlan, ...] | list[ActionPlan],
    ) -> tuple[ActionSimulation, ...]:
        return tuple(self.simulate(plan) for plan in plans)

    def _build_outcomes(
        self,
        plan: ActionPlan,
        evidence_ids: Tuple[str, ...],
    ) -> Tuple[SimulationOutcome, ...]:
        return (
            SimulationOutcome(
                outcome_id=f"SOUT-{plan.plan_id}-1",
                outcome_type="operational_response",
                description=(
                    "The proposed action may address the operational "
                    "condition represented by the decision."
                ),
                probability=0.60,
                confidence=0.55,
                affected_user_ids=plan.affected_user_ids,
                affected_system_ids=plan.affected_system_ids,
                evidence_ids=evidence_ids,
                data={
                    "simulated_step_count": plan.step_count,
                    "priority": plan.priority,
                },
            ),
        )

    def _build_risks(
        self,
        plan: ActionPlan,
        evidence_ids: Tuple[str, ...],
    ) -> Tuple[SimulationRisk, ...]:
        severity = {
            "low": "warning",
            "normal": "warning",
            "high": "high",
            "critical": "critical",
        }.get(plan.priority, "warning")

        return (
            SimulationRisk(
                risk_id=f"SRISK-{plan.plan_id}-1",
                risk_type="implementation_uncertainty",
                description=(
                    "The simulated outcome may differ from the "
                    "expected operational response."
                ),
                probability=0.35,
                severity=severity,
                mitigation=(
                    "Review the proposed plan and its expected impact "
                    "before approving any action."
                ),
                evidence_ids=evidence_ids,
            ),
        )

    def _confidence(self, plan: ActionPlan) -> float:
        source_confidence = plan.metadata.get("confidence", 0.0)

        try:
            source_confidence = float(source_confidence)
        except (TypeError, ValueError):
            source_confidence = 0.0

        source_confidence = max(0.0, min(1.0, source_confidence))

        if plan.evidence:
            return round(
                min(1.0, 0.5 * source_confidence + 0.5 * 0.60),
                6,
            )

        return round(0.5 * source_confidence, 6)
