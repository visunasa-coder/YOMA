from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from yoma.office.decision_intelligence import DecisionIntelligence


@dataclass(frozen=True)
class ActionPlanEvidence:
    evidence_id: str
    source_id: str
    description: str = ""
    weight: float = 0.0
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id must not be empty")
        if not self.source_id:
            raise ValueError("source_id must not be empty")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0 and 1")


@dataclass(frozen=True)
class ActionPlanStep:
    step_id: str
    sequence: int
    action_type: str
    description: str
    target_user_id: Optional[str] = None
    target_system_id: Optional[str] = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    evidence_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("step_id must not be empty")
        if self.sequence < 1:
            raise ValueError("sequence must be >= 1")
        if not self.action_type:
            raise ValueError("action_type must not be empty")
        if not self.description:
            raise ValueError("description must not be empty")
        if not self.requires_human_approval:
            raise ValueError("action plan steps must require human approval")


@dataclass(frozen=True)
class ActionPlan:
    plan_id: str
    decision_id: str
    created_at: datetime
    decision_type: str
    priority: str
    reason: str
    steps: Tuple[ActionPlanStep, ...] = ()
    evidence: Tuple[ActionPlanEvidence, ...] = ()
    affected_user_ids: Tuple[str, ...] = ()
    affected_system_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")
        if not self.requires_human_approval:
            raise ValueError("action plans must require human approval")

        sequences = [step.sequence for step in self.steps]
        if sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("steps must have contiguous sequence numbers")

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def requires_review(self) -> bool:
        return self.requires_human_approval

    @property
    def executable(self) -> bool:
        return False


class ActionPlanningEngine:
    """
    Converts DecisionIntelligence into an advisory action plan.

    This module deliberately does not execute actions.
    """

    def build(self, decision: DecisionIntelligence) -> ActionPlan:
        if not isinstance(decision, DecisionIntelligence):
            raise TypeError("decision must be a DecisionIntelligence")

        evidence = tuple(
            ActionPlanEvidence(
                evidence_id=evidence.evidence_id,
                source_id=evidence.source_id,
                description=evidence.description,
                weight=evidence.weight,
                data=dict(evidence.data),
            )
            for evidence in decision.evidence
        )

        steps = self._build_steps(decision)

        affected_users = tuple(
            sorted(
                {
                    decision.user_id,
                    *(
                        step.target_user_id
                        for step in steps
                        if step.target_user_id
                    ),
                }
                - {None}
            )
        )

        affected_systems = tuple(
            sorted(
                {
                    decision.system_id,
                    *(
                        step.target_system_id
                        for step in steps
                        if step.target_system_id
                    ),
                }
                - {None}
            )
        )

        return ActionPlan(
            plan_id=f"APLAN-{decision.decision_id}",
            decision_id=decision.decision_id,
            created_at=decision.created_at,
            decision_type=decision.decision_type,
            priority=decision.priority,
            reason=decision.recommendation_reason
            or "Decision requires human-reviewed operational planning.",
            steps=steps,
            evidence=evidence,
            affected_user_ids=affected_users,
            affected_system_ids=affected_systems,
            requires_human_approval=True,
            metadata={
                "recommendation_type": decision.recommendation_type,
                "confidence": decision.confidence,
            },
        )

    def build_many(
        self,
        decisions: tuple[DecisionIntelligence, ...] | list[DecisionIntelligence],
    ) -> tuple[ActionPlan, ...]:
        return tuple(self.build(decision) for decision in decisions)

    def _build_steps(
        self,
        decision: DecisionIntelligence,
    ) -> Tuple[ActionPlanStep, ...]:
        recommendation = decision.recommendation_type or "decision_review"

        return (
            ActionPlanStep(
                step_id=f"ASTEP-{decision.decision_id}-1",
                sequence=1,
                action_type=recommendation,
                description=(
                    decision.recommendation_reason
                    or "Review the decision and determine the appropriate action."
                ),
                target_user_id=decision.user_id,
                target_system_id=decision.system_id,
                parameters={
                    "decision_id": decision.decision_id,
                    "priority": decision.priority,
                    "confidence": decision.confidence,
                },
                evidence_ids=tuple(
                    evidence.evidence_id for evidence in decision.evidence
                ),
                requires_human_approval=True,
            ),
        )
