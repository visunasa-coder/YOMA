from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.decision_intelligence_runtime import (
    DecisionIntelligenceRuntime,
)
from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.decision_explanation import DecisionExplanation


@dataclass(frozen=True)
class ControlServerDecisionIntelligenceStatus:
    available: bool
    running: bool
    decision_count: int
    explanation_count: int
    requires_human_review: bool

    @property
    def ready(self) -> bool:
        return self.available and self.running


class ControlServerDecisionIntelligence:
    """Expose Decision Intelligence through the existing Control Server runtime.

    This adapter does not create another server, event bus, or execution path.
    It only provides a read-oriented integration boundary for M30 Decision
    Intelligence.
    """

    def __init__(
        self,
        control_server_runtime: ControlServerRuntime,
        decision_runtime: DecisionIntelligenceRuntime,
    ) -> None:
        if not isinstance(
            control_server_runtime,
            ControlServerRuntime,
        ):
            raise TypeError(
                "control_server_runtime must be a ControlServerRuntime"
            )

        if not isinstance(
            decision_runtime,
            DecisionIntelligenceRuntime,
        ):
            raise TypeError(
                "decision_runtime must be a DecisionIntelligenceRuntime"
            )

        self._control_server_runtime = control_server_runtime
        self._decision_runtime = decision_runtime

    @property
    def control_server_runtime(self) -> ControlServerRuntime:
        return self._control_server_runtime

    @property
    def decision_runtime(self) -> DecisionIntelligenceRuntime:
        return self._decision_runtime

    @property
    def running(self) -> bool:
        return self._control_server_runtime.running

    def status(self) -> ControlServerDecisionIntelligenceStatus:
        result = self._decision_runtime.last_result

        if result is None:
            return ControlServerDecisionIntelligenceStatus(
                available=False,
                running=self.running,
                decision_count=0,
                explanation_count=0,
                requires_human_review=False,
            )

        return ControlServerDecisionIntelligenceStatus(
            available=result.decision_count > 0,
            running=self.running,
            decision_count=result.decision_count,
            explanation_count=result.explanation_count,
            requires_human_review=result.requires_human_review,
        )

    def latest(self) -> Optional[dict[str, Any]]:
        result = self._decision_runtime.last_result

        if result is None:
            return None

        decisions = tuple(
            self._decision_payload(decision)
            for decision in result.decisions
        )

        explanations = tuple(
            self._explanation_payload(explanation)
            for explanation in result.explanations
        )

        return {
            "decision_count": result.decision_count,
            "graph_count": result.graph_count,
            "explanation_count": result.explanation_count,
            "requires_human_review": result.requires_human_review,
            "decisions": decisions,
            "explanations": explanations,
        }

    @staticmethod
    def _decision_payload(
        decision: DecisionIntelligence,
    ) -> dict[str, Any]:
        return {
            "decision_id": decision.decision_id,
            "decision_type": decision.decision_type,
            "organization_id": decision.organization_id,
            "user_id": decision.user_id,
            "system_id": decision.system_id,
            "situation_type": decision.situation_type,
            "priority": decision.priority,
            "confidence": decision.confidence,
            "current_intelligence_available": (
                decision.current_intelligence_available
            ),
            "historical_intelligence_available": (
                decision.historical_intelligence_available
            ),
            "predictive_intelligence_available": (
                decision.predictive_intelligence_available
            ),
            "recommendation_type": decision.recommendation_type,
            "recommendation_reason": decision.recommendation_reason,
            "requires_human_approval": decision.requires_human_approval,
        }

    @staticmethod
    def _explanation_payload(
        explanation: DecisionExplanation,
    ) -> dict[str, Any]:
        return {
            "explanation_id": explanation.explanation_id,
            "decision_id": explanation.decision_id,
            "summary": explanation.summary,
            "why_it_matters": explanation.why_it_matters,
            "supporting_evidence": explanation.supporting_evidence,
            "current_context": explanation.current_context,
            "historical_context": explanation.historical_context,
            "predictive_context": explanation.predictive_context,
            "uncertainty": explanation.uncertainty,
            "recommendation": explanation.recommendation,
            "priority": explanation.priority,
            "priority_score": explanation.priority_score,
            "confidence": explanation.confidence,
            "requires_human_approval": (
                explanation.requires_human_approval
            ),
        }


__all__ = [
    "ControlServerDecisionIntelligence",
    "ControlServerDecisionIntelligenceStatus",
]
