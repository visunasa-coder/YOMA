from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.decision_evidence_graph import DecisionEvidenceGraph
from yoma.office.decision_priority import DecisionPriorityScore


@dataclass(frozen=True)
class DecisionExplanation:
    explanation_id: str
    decision_id: str
    summary: str
    why_it_matters: str
    supporting_evidence: tuple[str, ...] = ()
    current_context: tuple[str, ...] = ()
    historical_context: tuple[str, ...] = ()
    predictive_context: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()
    recommendation: str = ""
    priority: str = "normal"
    priority_score: float = 0.0
    confidence: float = 0.0
    requires_human_approval: bool = True

    @property
    def evidence_count(self) -> int:
        return len(self.supporting_evidence)

    @property
    def context_count(self) -> int:
        return (
            len(self.current_context)
            + len(self.historical_context)
            + len(self.predictive_context)
        )

    @property
    def explainable(self) -> bool:
        return bool(
            self.summary
            and self.evidence_count > 0
            and any(
                not item.startswith("No explicit evidence nodes")
                for item in self.supporting_evidence
            )
        )

    @property
    def uncertainty_level(self) -> str:
        if self.confidence >= 0.80:
            return "low"
        if self.confidence >= 0.60:
            return "moderate"
        return "high"


class DecisionExplanationEngine:
    """Build deterministic, evidence-backed explanations for decisions.

    This layer explains existing decision intelligence. It does not create,
    approve, or execute operational actions.
    """

    def explain(
        self,
        decision: DecisionIntelligence,
        graph: DecisionEvidenceGraph,
        priority_score: Optional[DecisionPriorityScore] = None,
    ) -> DecisionExplanation:
        if not isinstance(decision, DecisionIntelligence):
            raise TypeError("decision must be a DecisionIntelligence")

        if not isinstance(graph, DecisionEvidenceGraph):
            raise TypeError("graph must be a DecisionEvidenceGraph")

        if graph.decision_id != decision.decision_id:
            raise ValueError(
                "graph.decision_id must match decision.decision_id"
            )

        if priority_score is not None:
            if not isinstance(priority_score, DecisionPriorityScore):
                raise TypeError(
                    "priority_score must be a DecisionPriorityScore or None"
                )
            if priority_score.decision_id != decision.decision_id:
                raise ValueError(
                    "priority_score.decision_id must match decision.decision_id"
                )

        current_context: list[str] = []
        historical_context: list[str] = []
        predictive_context: list[str] = []
        supporting_evidence: list[str] = []

        for node in graph.nodes:
            if node.node_type == "current_decision":
                current_context.append(node.node_id)
            elif node.node_type == "historical_context":
                historical_context.append(node.node_id)
            elif node.node_type == "predictive_context":
                predictive_context.append(node.node_id)
            elif node.node_type == "evidence":
                supporting_evidence.append(node.node_id)

        current_context.sort()
        historical_context.sort()
        predictive_context.sort()
        supporting_evidence.sort()

        context_parts: list[str] = []

        if current_context:
            context_parts.append(
                f"{len(current_context)} current decision context"
                + ("s" if len(current_context) != 1 else "")
            )

        if historical_context:
            context_parts.append(
                f"{len(historical_context)} historical context"
                + ("s" if len(historical_context) != 1 else "")
            )

        if predictive_context:
            context_parts.append(
                f"{len(predictive_context)} predictive context"
                + ("s" if len(predictive_context) != 1 else "")
            )

        if context_parts:
            summary = (
                f"Decision {decision.decision_id} is supported by "
                + ", ".join(context_parts)
                + "."
            )
        else:
            summary = (
                f"Decision {decision.decision_id} has limited contextual "
                "support."
            )

        if decision.situation_type:
            why_it_matters = (
                f"The decision relates to the operational situation "
                f"'{decision.situation_type}' with "
                f"{decision.priority} priority and "
                f"{decision.confidence:.2f} confidence."
            )
        else:
            why_it_matters = (
                f"The decision has {decision.priority} priority and "
                f"{decision.confidence:.2f} confidence."
            )

        decision_evidence_ids = {
            evidence.evidence_id
            for evidence in decision.evidence
        }

        actual_evidence = tuple(
            node_id
            for node_id in supporting_evidence
            if node_id in decision_evidence_ids
        )

        if actual_evidence:
            evidence_text = tuple(
                f"Evidence node {node_id} supports the decision."
                for node_id in actual_evidence
            )
        else:
            evidence_text = (
                "No explicit evidence nodes are attached to this decision.",
            )

        uncertainty: list[str] = []

        if decision.confidence < 0.60:
            uncertainty.append(
                "Decision confidence is below 0.60."
            )
        elif decision.confidence < 0.80:
            uncertainty.append(
                "Decision confidence is moderate."
            )

        if not historical_context:
            uncertainty.append(
                "No historical context is attached to this decision."
            )

        if not predictive_context:
            uncertainty.append(
                "No predictive context is attached to this decision."
            )

        if not supporting_evidence:
            uncertainty.append(
                "The decision has no explicit evidence nodes."
            )

        if not uncertainty:
            uncertainty.append(
                "No major uncertainty was identified by the explanation layer."
            )

        if decision.recommendation_type:
            recommendation = decision.recommendation_reason or (
                f"Review the recommended action type "
                f"'{decision.recommendation_type}'."
            )
        else:
            recommendation = (
                "Review the decision using the attached evidence and context."
            )

        if priority_score is not None:
            priority = priority_score.priority
            priority_value = priority_score.total_score
        else:
            priority = decision.priority
            priority_value = 0.0

        explanation_id = f"DEXP-{decision.decision_id}"

        return DecisionExplanation(
            explanation_id=explanation_id,
            decision_id=decision.decision_id,
            summary=summary,
            why_it_matters=why_it_matters,
            supporting_evidence=tuple(evidence_text),
            current_context=tuple(current_context),
            historical_context=tuple(historical_context),
            predictive_context=tuple(predictive_context),
            uncertainty=tuple(uncertainty),
            recommendation=recommendation,
            priority=priority,
            priority_score=priority_value,
            confidence=decision.confidence,
            requires_human_approval=True,
        )

    def explain_many(
        self,
        decisions: Iterable[DecisionIntelligence],
        graphs: Iterable[DecisionEvidenceGraph],
        priority_scores: Iterable[DecisionPriorityScore] = (),
    ) -> tuple[DecisionExplanation, ...]:
        decisions_by_id = {
            decision.decision_id: decision
            for decision in decisions
        }

        graphs_by_id = {
            graph.decision_id: graph
            for graph in graphs
        }

        scores_by_id = {
            score.decision_id: score
            for score in priority_scores
        }

        results: list[DecisionExplanation] = []

        for decision_id in sorted(decisions_by_id):
            decision = decisions_by_id[decision_id]
            graph = graphs_by_id.get(decision_id)

            if graph is None:
                raise ValueError(
                    f"No evidence graph found for decision {decision_id}"
                )

            results.append(
                self.explain(
                    decision,
                    graph,
                    scores_by_id.get(decision_id),
                )
            )

        return tuple(results)


__all__ = [
    "DecisionExplanation",
    "DecisionExplanationEngine",
]
