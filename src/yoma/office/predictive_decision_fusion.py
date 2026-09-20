from __future__ import annotations

from typing import Iterable, Optional

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.decision_intelligence import (
    DecisionIntelligence,
    DecisionIntelligenceEvidence,
)
from yoma.office.current_historical_decision_fusion import (
    CurrentHistoricalDecisionFusion,
)
from yoma.office.predictive_decision_context import (
    PredictiveDecisionContext,
)


class PredictiveDecisionFusion:
    """
    M30.3

    Extends the validated M30.2 current + historical fusion layer
    with predictive decision intelligence.

    Architecture:

        Current Decision
              +
        Historical Intelligence
              +
        Predictive Intelligence
              ↓
        DecisionIntelligence

    Advisory only. No autonomous action execution.
    """

    def __init__(
        self,
        current_decisions: Iterable[DecisionContext] = (),
        historical_contexts=(),
        predictive_contexts: Iterable[PredictiveDecisionContext] = (),
    ) -> None:
        self._current_decisions = tuple(current_decisions)
        self._historical_contexts = tuple(historical_contexts)
        self._predictive_contexts = tuple(predictive_contexts)

        self._current_historical = CurrentHistoricalDecisionFusion(
            current_decisions=self._current_decisions,
            historical_contexts=self._historical_contexts,
        )

    @staticmethod
    def _scope_matches(
        current: DecisionContext,
        predictive: PredictiveDecisionContext,
    ) -> bool:
        signal = current.signal

        return (
            signal.organization_id == predictive.organization_id
            and signal.user_id == predictive.user_id
            and signal.system_id == predictive.system_id
        )

    @staticmethod
    def _situation_matches(
        current: DecisionContext,
        predictive: PredictiveDecisionContext,
    ) -> bool:
        """
        Predictive contexts are generated from the same operational
        signal family. Accept the exact signal type, and the known
        workload-pressure normalization used by YOMA's operational
        intelligence layers.
        """
        current_type = current.signal.signal_type
        predictive_type = predictive.situation_type

        if current_type == predictive_type:
            return True

        aliases = {
            "workload.high": {"workload_pressure"},
            "workload_pressure": {"workload.high"},
        }

        return predictive_type in aliases.get(
            current_type,
            set(),
        )

    @staticmethod
    def _predictive_available(
        predictive: PredictiveDecisionContext,
    ) -> bool:
        return (
            predictive.probability > 0.0
            or predictive.confidence > 0.0
            or bool(predictive.evidence_situation_ids)
            or bool(predictive.evidence)
        )

    def _find_predictive(
        self,
        current: DecisionContext,
    ) -> Optional[PredictiveDecisionContext]:
        matches = [
            context
            for context in self._predictive_contexts
            if self._scope_matches(current, context)
            and self._situation_matches(current, context)
            and self._predictive_available(context)
        ]

        if not matches:
            return None

        return sorted(
            matches,
            key=lambda context: (
                -float(context.probability),
                -float(context.confidence),
                context.context_id,
            ),
        )[0]

    @staticmethod
    def _predictive_evidence(
        predictive: PredictiveDecisionContext,
    ) -> DecisionIntelligenceEvidence:
        weight = (
            float(predictive.probability)
            + float(predictive.confidence)
        ) / 2.0

        return DecisionIntelligenceEvidence(
            evidence_id=f"PRED-{predictive.prediction_id}",
            evidence_type="predictive_decision_context",
            source_id=predictive.context_id,
            description=(
                "Predictive intelligence indicates future "
                "operational risk or recurrence."
            ),
            weight=round(
                max(0.0, min(1.0, weight)),
                6,
            ),
            data={
                "prediction_id": predictive.prediction_id,
                "probability": predictive.probability,
                "confidence": predictive.confidence,
                "severity": predictive.severity,
            },
        )

    @staticmethod
    def _combined_confidence(
        current: DecisionContext,
        base: DecisionIntelligence,
        predictive: Optional[PredictiveDecisionContext],
    ) -> float:
        """
        Preserve the M30.2 confidence when no predictive context exists.

        When predictive intelligence exists, combine the already-fused
        M30.2 confidence with predictive probability/confidence.
        """
        if predictive is None:
            return base.confidence

        values = [
            float(base.confidence),
            float(predictive.probability),
            float(predictive.confidence),
        ]

        return round(
            max(
                0.0,
                min(
                    1.0,
                    sum(values) / len(values),
                ),
            ),
            6,
        )

    @staticmethod
    def _priority(
        base_priority: str,
        predictive_priority: str,
        predictive_severity: str,
    ) -> str:
        rank = {
            "low": 0,
            "normal": 1,
            "warning": 1,
            "high": 2,
            "critical": 3,
        }

        base_rank = rank.get(base_priority, 1)
        predictive_rank = rank.get(predictive_priority, 1)
        severity_rank = rank.get(predictive_severity, 1)

        highest = max(
            base_rank,
            predictive_rank,
            severity_rank,
        )

        for name, value in rank.items():
            if value == highest and name in {
                "low",
                "normal",
                "high",
                "critical",
            }:
                return name

        return base_priority

    def fuse(
        self,
        current: DecisionContext,
    ) -> DecisionIntelligence:
        if not isinstance(current, DecisionContext):
            raise TypeError(
                "current must be a DecisionContext"
            )

        # M30.2 is the authoritative current + historical layer.
        base = self._current_historical.fuse(current)

        predictive = self._find_predictive(current)

        if predictive is None:
            return DecisionIntelligence(
                decision_id=base.decision_id,
                decision_type=base.decision_type,
                created_at=base.created_at,
                organization_id=base.organization_id,
                user_id=base.user_id,
                system_id=base.system_id,
                situation_type=base.situation_type,
                priority=base.priority,
                confidence=base.confidence,
                current_intelligence_available=(
                    base.current_intelligence_available
                ),
                historical_intelligence_available=(
                    base.historical_intelligence_available
                ),
                predictive_intelligence_available=False,
                current_decision_ids=(
                    base.current_decision_ids
                ),
                historical_context_ids=(
                    base.historical_context_ids
                ),
                predictive_context_ids=(),
                evidence=base.evidence,
                recommendation_type=(
                    base.recommendation_type
                ),
                recommendation_reason=(
                    base.recommendation_reason
                ),
                requires_human_approval=True,
                metadata={
                    **base.metadata,
                    "fusion": (
                        "current_historical_predictive"
                    ),
                    "predictive_match": False,
                },
            )

        evidence = list(base.evidence)
        evidence.append(
            self._predictive_evidence(predictive)
        )

        recommendation_type = base.recommendation_type
        recommendation_reason = base.recommendation_reason

        if recommendation_type is None:
            recommendation_type = (
                predictive.recommendation.recommendation_type
            )

        if not recommendation_reason:
            recommendation_reason = (
                predictive.recommendation.reason
            )

        priority = self._priority(
            base.priority,
            predictive.recommendation.priority,
            predictive.severity,
        )

        confidence = self._combined_confidence(
            current,
            base,
            predictive,
        )

        metadata = {
            **base.metadata,
            "fusion": (
                "current_historical_predictive"
            ),
            "predictive_match": True,
            "prediction_id": predictive.prediction_id,
            "predictive_probability": (
                predictive.probability
            ),
            "predictive_confidence": (
                predictive.confidence
            ),
            "predictive_severity": (
                predictive.severity
            ),
        }

        return DecisionIntelligence(
            decision_id=base.decision_id,
            decision_type=(
                recommendation_type
                or base.decision_type
            ),
            created_at=base.created_at,
            organization_id=base.organization_id,
            user_id=base.user_id,
            system_id=base.system_id,
            situation_type=base.situation_type,
            priority=priority,
            confidence=confidence,
            current_intelligence_available=(
                base.current_intelligence_available
            ),
            historical_intelligence_available=(
                base.historical_intelligence_available
            ),
            predictive_intelligence_available=True,
            current_decision_ids=(
                base.current_decision_ids
            ),
            historical_context_ids=(
                base.historical_context_ids
            ),
            predictive_context_ids=(
                predictive.context_id,
            ),
            evidence=tuple(evidence),
            recommendation_type=recommendation_type,
            recommendation_reason=recommendation_reason,
            requires_human_approval=True,
            metadata=metadata,
        )

    def fuse_many(
        self,
        current_decisions: Optional[
            Iterable[DecisionContext]
        ] = None,
    ) -> tuple[DecisionIntelligence, ...]:
        decisions = (
            tuple(current_decisions)
            if current_decisions is not None
            else self._current_decisions
        )

        results = [
            self.fuse(decision)
            for decision in decisions
        ]

        return tuple(
            sorted(
                results,
                key=lambda result: result.decision_id,
            )
        )
