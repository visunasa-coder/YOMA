"""M30.2 current + historical decision fusion.

Combines current operational decision contexts with matching historical
decision contexts for advisory decision intelligence.

No actions are executed and human approval remains mandatory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.historical_decision_context import HistoricalDecisionContext


class CurrentHistoricalDecisionFusion:
    """Fuse current operational decisions with historical intelligence."""

    def __init__(
        self,
        current_decisions: Iterable[DecisionContext] = (),
        historical_contexts: Iterable[HistoricalDecisionContext] = (),
    ) -> None:
        self._current_decisions = tuple(current_decisions)
        self._historical_contexts = tuple(historical_contexts)

    @staticmethod
    def _scope_matches(
        current: DecisionContext,
        historical: HistoricalDecisionContext,
    ) -> bool:
        signal = current.signal

        return (
            signal.organization_id == historical.organization_id
            and signal.user_id == historical.user_id
            and signal.system_id == historical.system_id
        )

    @staticmethod
    def _situation_matches(
        current: DecisionContext,
        historical: HistoricalDecisionContext,
    ) -> bool:
        signal_type = current.signal.signal_type
        situation_type = historical.situation_type

        return (
            signal_type == situation_type
            or signal_type.startswith(f"{situation_type}.")
            or situation_type.startswith(f"{signal_type}.")
            or signal_type.replace(".high", "") == situation_type
            or situation_type.replace(".high", "") == signal_type
        )

    @staticmethod
    def _historical_available(
        historical: HistoricalDecisionContext,
    ) -> bool:
        # Historical fusion requires repeated historical evidence.
        # A single occurrence is not sufficient historical intelligence.
        return historical.occurrence_count >= 2

    @staticmethod
    def _priority(score: float) -> str:
        if score >= 0.85:
            return "critical"
        if score >= 0.65:
            return "high"
        if score >= 0.40:
            return "normal"
        return "low"

    @staticmethod
    def _historical_strength(
        historical: HistoricalDecisionContext,
    ) -> float:
        """Convert historical deviation into a bounded evidence strength."""
        deviation = abs(float(historical.deviation_from_baseline))

        if deviation <= 1.0:
            return round(deviation, 6)

        return round(deviation / (1.0 + deviation), 6)

    @staticmethod
    def _confidence(
        current: DecisionContext,
        historical: Optional[HistoricalDecisionContext],
    ) -> float:
        current_score = max(
            0.0,
            min(1.0, float(current.signal.score)),
        )

        if historical is None:
            return round(current_score, 6)

        historical_score = CurrentHistoricalDecisionFusion._historical_strength(
            historical
        )

        return round(
            max(
                0.0,
                min(
                    1.0,
                    (current_score + historical_score) / 2.0,
                ),
            ),
            6,
        )

    def _find_historical(
        self,
        current: DecisionContext,
    ) -> Optional[HistoricalDecisionContext]:
        matches = [
            historical
            for historical in self._historical_contexts
            if self._scope_matches(current, historical)
            and self._situation_matches(current, historical)
            and self._historical_available(historical)
        ]

        if not matches:
            return None

        return sorted(
            matches,
            key=lambda item: (
                -item.occurrence_count,
                item.situation_id,
                item.historical_pattern_id or "",
            ),
        )[0]

    @staticmethod
    def _recommendation_type(current: DecisionContext) -> str:
        if not current.recommendations:
            return "operational_review"

        recommendation = current.recommendations[0]

        if isinstance(recommendation, dict):
            return str(
                recommendation.get(
                    "type",
                    "operational_review",
                )
            )

        return "operational_review"

    @staticmethod
    def _recommendation_reason(current: DecisionContext) -> str:
        if not current.recommendations:
            return (
                f"Current signal {current.signal.signal_type} "
                "requires human review."
            )

        recommendation = current.recommendations[0]

        if isinstance(recommendation, dict):
            return str(
                recommendation.get(
                    "reason",
                    f"Current signal {current.signal.signal_type} "
                    "requires human review.",
                )
            )

        return (
            f"Current signal {current.signal.signal_type} "
            "requires human review."
        )

    def fuse(self, current: DecisionContext) -> DecisionIntelligence:
        if not isinstance(current, DecisionContext):
            raise TypeError("current must be a DecisionContext")

        signal = current.signal
        historical = self._find_historical(current)

        confidence = self._confidence(current, historical)

        recommendation_type = self._recommendation_type(current)
        recommendation_reason = self._recommendation_reason(current)

        current_id = f"DEC-{signal.signal_id}"

        evidence = [
            DecisionIntelligenceEvidence(
                evidence_id=f"CURRENT-{signal.signal_id}",
                evidence_type="current",
                source_id=signal.signal_id,
                description=(
                    f"Current operational signal: {signal.signal_type}"
                ),
                weight=round(
                    max(0.0, min(1.0, float(signal.score))),
                    6,
                ),
            )
        ]

        historical_ids: Tuple[str, ...] = ()
        historical_available = False

        if historical is not None:
            historical_available = True
            historical_ids = (historical.situation_id,)

            evidence.append(
                DecisionIntelligenceEvidence(
                    evidence_id=f"HIST-{historical.situation_id}",
                    evidence_type="historical",
                    source_id=historical.situation_id,
                    description=(
                        f"Historical context for "
                        f"{historical.situation_type}"
                    ),
                    weight=self._historical_strength(historical),
                )
            )

            recommendation_reason += (
                f" Historical intelligence shows "
                f"{historical.occurrence_count} occurrence(s) "
                f"for the same operational situation."
            )

        decision_id = (
            f"DINT-{signal.organization_id or 'GLOBAL'}-"
            f"{signal.user_id or 'GLOBAL'}-"
            f"{signal.system_id or 'GLOBAL'}-"
            f"{signal.signal_id}"
        )

        return DecisionIntelligence(
            decision_id=decision_id,
            decision_type=recommendation_type,
            created_at=signal.detected_at,
            organization_id=signal.organization_id,
            user_id=signal.user_id,
            system_id=signal.system_id,
            situation_type=signal.signal_type,
            priority=self._priority(confidence),
            confidence=confidence,
            current_intelligence_available=True,
            historical_intelligence_available=historical_available,
            predictive_intelligence_available=False,
            current_decision_ids=(current_id,),
            historical_context_ids=historical_ids,
            predictive_context_ids=(),
            evidence=tuple(evidence),
            recommendation_type=recommendation_type,
            recommendation_reason=recommendation_reason,
            requires_human_approval=True,
            metadata={
                "fusion": "current_historical",
                "historical_match": historical is not None,
            },
        )

    def fuse_many(
        self,
        current_decisions: Iterable[DecisionContext],
    ) -> Tuple[DecisionIntelligence, ...]:
        results = tuple(
            self.fuse(decision)
            for decision in current_decisions
        )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.organization_id or "",
                    item.user_id or "",
                    item.system_id or "",
                    item.decision_id,
                ),
            )
        )
