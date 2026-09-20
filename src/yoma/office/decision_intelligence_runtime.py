from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.current_historical_decision_fusion import (
    CurrentHistoricalDecisionFusion,
)
from yoma.office.predictive_decision_fusion import (
    PredictiveDecisionFusion,
)
from yoma.office.decision_priority import (
    DecisionPriorityRanker,
    DecisionPriorityRanking,
    DecisionPriorityRanking,
)
from yoma.office.decision_evidence_graph import (
    DecisionEvidenceGraph,
    DecisionEvidenceGraphBuilder,
)
from yoma.office.decision_explanation import (
    DecisionExplanation,
    DecisionExplanationEngine,
)


@dataclass(frozen=True)
class DecisionIntelligenceResult:
    decisions: tuple[DecisionIntelligence, ...] = ()
    ranking: Optional[DecisionPriorityRanking] = None
    graphs: tuple[DecisionEvidenceGraph, ...] = ()
    explanations: tuple[DecisionExplanation, ...] = ()

    @property
    def decision_count(self) -> int:
        return len(self.decisions)

    @property
    def graph_count(self) -> int:
        return len(self.graphs)

    @property
    def explanation_count(self) -> int:
        return len(self.explanations)

    @property
    def top_decision(self) -> Optional[DecisionIntelligence]:
        if self.ranking is None:
            return None
        return self.ranking.top_decision

    @property
    def requires_human_review(self) -> bool:
        return any(
            decision.requires_human_approval
            for decision in self.decisions
        )

    @property
    def intelligence_available(self) -> bool:
        return any(
            decision.intelligence_available
            for decision in self.decisions
        )


class DecisionIntelligenceRuntime:
    """Unified advisory Decision Intelligence runtime.

    Composes the existing M30 fusion, ranking, evidence graph, and
    explanation layers. This runtime does not execute actions.
    """

    def __init__(
        self,
        current_decisions: Iterable = (),
        historical_contexts: Iterable = (),
        predictive_contexts: Iterable = (),
        fusion: Optional[PredictiveDecisionFusion] = None,
        ranker: Optional[DecisionPriorityRanker] = None,
        graph_builder: Optional[DecisionEvidenceGraphBuilder] = None,
        explanation_engine: Optional[DecisionExplanationEngine] = None,
    ) -> None:
        self._current_decisions = tuple(current_decisions)
        self._historical_contexts = tuple(historical_contexts)
        self._predictive_contexts = tuple(predictive_contexts)

        self._fusion = fusion or PredictiveDecisionFusion(
            current_decisions=self._current_decisions,
            historical_contexts=self._historical_contexts,
            predictive_contexts=self._predictive_contexts,
        )

        self._ranker = ranker or DecisionPriorityRanker()
        self._graph_builder = (
            graph_builder or DecisionEvidenceGraphBuilder()
        )
        self._explanation_engine = (
            explanation_engine or DecisionExplanationEngine()
        )

        self._last_result: Optional[DecisionIntelligenceResult] = None

    @property
    def last_result(self) -> Optional[DecisionIntelligenceResult]:
        return self._last_result

    @property
    def decision_count(self) -> int:
        if self._last_result is None:
            return 0
        return self._last_result.decision_count

    def analyze(
        self,
        current_decisions: Optional[Iterable] = None,
        historical_contexts: Optional[Iterable] = None,
        predictive_contexts: Optional[Iterable] = None,
    ) -> DecisionIntelligenceResult:
        current = (
            self._current_decisions
            if current_decisions is None
            else tuple(current_decisions)
        )

        historical = (
            self._historical_contexts
            if historical_contexts is None
            else tuple(historical_contexts)
        )

        predictive = (
            self._predictive_contexts
            if predictive_contexts is None
            else tuple(predictive_contexts)
        )

        fusion = PredictiveDecisionFusion(
            current_decisions=current,
            historical_contexts=historical,
            predictive_contexts=predictive,
        )

        decisions = tuple(
            fusion.fuse_many(
                current,
            )
        )

        decisions = tuple(
            decision
            for decision in decisions
            if isinstance(decision, DecisionIntelligence)
        )

        ranking = self._ranker.rank(decisions)

        if not isinstance(ranking, DecisionPriorityRanking):
            raise TypeError(
                "DecisionPriorityRanker.rank() must return "
                "DecisionPriorityRanking."
            )

        graphs = self._graph_builder.build_many(decisions)

        scores = ranking.scores

        explanations = self._explanation_engine.explain_many(
            decisions,
            graphs,
            scores,
        )

        for decision in decisions:
            if not decision.requires_human_approval:
                raise ValueError(
                    "Decision Intelligence runtime requires human approval."
                )

        result = DecisionIntelligenceResult(
            decisions=decisions,
            ranking=ranking,
            graphs=graphs,
            explanations=explanations,
        )

        self._last_result = result
        return result

    def analyze_one(
        self,
        current_decision,
        historical_contexts: Iterable = (),
        predictive_contexts: Iterable = (),
    ) -> DecisionIntelligenceResult:
        return self.analyze(
            current_decisions=(current_decision,),
            historical_contexts=historical_contexts,
            predictive_contexts=predictive_contexts,
        )

    def clear_last_result(self) -> None:
        self._last_result = None


__all__ = [
    "DecisionIntelligenceResult",
    "DecisionIntelligenceRuntime",
]
