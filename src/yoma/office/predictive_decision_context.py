"""M29.6 predictive decision context for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from yoma.office.predictive_situation import PredictiveSituation


@dataclass(frozen=True)
class PredictiveDecisionRecommendation:
    """Advisory recommendation generated from a predicted situation."""

    recommendation_id: str
    recommendation_type: str
    reason: str
    priority: str
    target_user_id: Optional[str]
    target_system_id: Optional[str]
    evidence: tuple[str, ...]
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if self.priority not in {
            "info",
            "warning",
            "high",
            "critical",
        }:
            raise ValueError(
                "priority must be info, warning, high, or critical"
            )


@dataclass(frozen=True)
class PredictiveDecisionContext:
    """Decision-ready advisory context for a predicted situation."""

    context_id: str
    prediction_id: str
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]
    created_at: datetime
    probability: float
    confidence: float
    severity: str
    forecast_start: Optional[datetime]
    forecast_end: Optional[datetime]
    recommendation: PredictiveDecisionRecommendation
    evidence_situation_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    actions: tuple[object, ...] = ()
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(
                "probability must be between 0 and 1"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if (
            self.forecast_start is not None
            and self.forecast_end is not None
            and self.forecast_end < self.forecast_start
        ):
            raise ValueError(
                "forecast_end must not precede forecast_start"
            )

        if self.actions:
            raise ValueError(
                "predictive decision contexts cannot contain executable actions"
            )

    @property
    def elevated(self) -> bool:
        return self.probability >= 0.60

    @property
    def decision_ready(self) -> bool:
        return bool(self.recommendation)

    @property
    def historical_evidence_available(self) -> bool:
        return bool(self.evidence_situation_ids)


class PredictiveDecisionContextBuilder:
    """
    Converts predictive situations into advisory decision contexts.

    This builder deliberately does not create executable actions.
    """

    @staticmethod
    def _priority(
        severity: str,
        probability: float,
    ) -> str:
        if severity == "critical":
            return "critical"

        if severity == "high":
            return "high"

        if probability >= 0.60:
            return "high"

        if severity == "warning":
            return "warning"

        return "info"

    @staticmethod
    def _recommendation_type(
        situation_type: str,
    ) -> str:
        return f"predictive_{situation_type}_review"

    def build(
        self,
        situation: PredictiveSituation,
    ) -> PredictiveDecisionContext:
        priority = self._priority(
            situation.severity,
            situation.probability,
        )

        recommendation_id = (
            f"PREC-{situation.prediction_id}"
        )

        recommendation = PredictiveDecisionRecommendation(
            recommendation_id=recommendation_id,
            recommendation_type=self._recommendation_type(
                situation.situation_type,
            ),
            reason=(
                "Predicted operational situation requires "
                "human review before any intervention."
            ),
            priority=priority,
            target_user_id=situation.user_id,
            target_system_id=situation.system_id,
            evidence=situation.evidence,
            requires_human_approval=True,
        )

        evidence = (
            f"prediction_id={situation.prediction_id}",
            f"probability={situation.probability:.6f}",
            f"confidence={situation.confidence:.6f}",
            f"severity={situation.severity}",
            f"priority={priority}",
            f"prediction_sources={','.join(situation.prediction_sources)}",
        ) + tuple(situation.evidence)

        return PredictiveDecisionContext(
            context_id=f"PDEC-{situation.prediction_id}",
            prediction_id=situation.prediction_id,
            situation_type=situation.situation_type,
            organization_id=situation.organization_id,
            user_id=situation.user_id,
            system_id=situation.system_id,
            created_at=situation.predicted_at,
            probability=situation.probability,
            confidence=situation.confidence,
            severity=situation.severity,
            forecast_start=situation.forecast_start,
            forecast_end=situation.forecast_end,
            recommendation=recommendation,
            evidence_situation_ids=situation.evidence_situation_ids,
            evidence=evidence,
            actions=(),
            requires_human_approval=True,
        )

    def build_many(
        self,
        situations: Sequence[PredictiveSituation],
    ) -> tuple[PredictiveDecisionContext, ...]:
        return tuple(
            self.build(situation)
            for situation in situations
        )
