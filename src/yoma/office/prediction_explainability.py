"""M29.7 prediction confidence and explainability for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from yoma.office.predictive_decision_context import (
    PredictiveDecisionContext,
)
from yoma.office.predictive_situation import PredictiveSituation


@dataclass(frozen=True)
class PredictionFactor:
    """A single explainable factor contributing to a prediction."""

    factor_type: str
    name: str
    value: str
    contribution: float
    evidence: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.contribution <= 1.0:
            raise ValueError(
                "contribution must be between 0 and 1"
            )


@dataclass(frozen=True)
class PredictionExplainability:
    """Confidence, evidence, uncertainty, and explanation for a prediction."""

    explanation_id: str
    prediction_id: str
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]
    confidence: float
    evidence_strength: float
    uncertainty: float
    confidence_level: str
    evidence_level: str
    factors: tuple[PredictionFactor, ...]
    evidence_situation_ids: tuple[str, ...]
    explanation: str
    limitations: tuple[str, ...]
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("confidence", self.confidence),
            ("evidence_strength", self.evidence_strength),
            ("uncertainty", self.uncertainty),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        if self.confidence_level not in {
            "low",
            "moderate",
            "high",
        }:
            raise ValueError(
                "confidence_level must be low, moderate, or high"
            )

        if self.evidence_level not in {
            "weak",
            "moderate",
            "strong",
        }:
            raise ValueError(
                "evidence_level must be weak, moderate, or strong"
            )

    @property
    def explainable(self) -> bool:
        return bool(self.explanation and self.factors)

    @property
    def uncertainty_level(self) -> str:
        if self.uncertainty >= 0.60:
            return "high"

        if self.uncertainty >= 0.30:
            return "moderate"

        return "low"


class PredictionExplainabilityEngine:
    """
    Produces deterministic explanations for predictive decision contexts.

    No model execution, persistence, or action execution occurs here.
    """

    @staticmethod
    def _confidence_level(
        confidence: float,
    ) -> str:
        if confidence >= 0.75:
            return "high"

        if confidence >= 0.50:
            return "moderate"

        return "low"

    @staticmethod
    def _evidence_level(
        strength: float,
    ) -> str:
        if strength >= 0.75:
            return "strong"

        if strength >= 0.50:
            return "moderate"

        return "weak"

    @staticmethod
    def _factor(
        factor_type: str,
        name: str,
        value: str,
        contribution: float,
        evidence: str,
    ) -> PredictionFactor:
        return PredictionFactor(
            factor_type=factor_type,
            name=name,
            value=value,
            contribution=round(
                max(0.0, min(1.0, contribution)),
                6,
            ),
            evidence=evidence,
        )

    def explain(
        self,
        context: PredictiveDecisionContext,
    ) -> PredictionExplainability:
        situation = PredictiveSituation(
            prediction_id=context.prediction_id,
            situation_type=context.situation_type,
            organization_id=context.organization_id,
            user_id=context.user_id,
            system_id=context.system_id,
            predicted_at=context.created_at,
            forecast_start=context.forecast_start,
            forecast_end=context.forecast_end,
            probability=context.probability,
            confidence=context.confidence,
            severity=context.severity,
            prediction_sources=tuple(
                self._extract_sources(context)
            ),
            evidence_situation_ids=context.evidence_situation_ids,
            evidence=context.evidence,
            requires_human_approval=True,
        )

        factors = self._build_factors(situation)

        evidence_strength = self._evidence_strength(
            situation,
            factors,
        )

        uncertainty = round(
            1.0 - situation.confidence,
            6,
        )

        confidence_level = self._confidence_level(
            situation.confidence
        )

        evidence_level = self._evidence_level(
            evidence_strength
        )

        explanation = self._build_explanation(
            situation,
            factors,
            evidence_strength,
            uncertainty,
        )

        limitations = self._build_limitations(
            situation,
            factors,
        )

        return PredictionExplainability(
            explanation_id=(
                f"EXPL-{context.prediction_id}"
            ),
            prediction_id=context.prediction_id,
            situation_type=context.situation_type,
            organization_id=context.organization_id,
            user_id=context.user_id,
            system_id=context.system_id,
            confidence=situation.confidence,
            evidence_strength=evidence_strength,
            uncertainty=uncertainty,
            confidence_level=confidence_level,
            evidence_level=evidence_level,
            factors=tuple(factors),
            evidence_situation_ids=(
                context.evidence_situation_ids
            ),
            explanation=explanation,
            limitations=tuple(limitations),
            requires_human_approval=True,
        )

    @staticmethod
    def _extract_sources(
        context: PredictiveDecisionContext,
    ) -> Sequence[str]:
        for item in context.evidence:
            if item.startswith("prediction_sources="):
                raw = item.split("=", 1)[1]
                if raw:
                    return tuple(
                        source
                        for source in raw.split(",")
                        if source
                    )

        return ()

    def _build_factors(
        self,
        situation: PredictiveSituation,
    ) -> list[PredictionFactor]:
        factors: list[PredictionFactor] = []

        if situation.probability > 0:
            factors.append(
                self._factor(
                    "probability",
                    "prediction_probability",
                    f"{situation.probability:.6f}",
                    situation.probability,
                    "Predicted probability supplied by the predictive layer.",
                )
            )

        if situation.confidence > 0:
            factors.append(
                self._factor(
                    "confidence",
                    "prediction_confidence",
                    f"{situation.confidence:.6f}",
                    situation.confidence,
                    "Confidence supplied by the predictive layer.",
                )
            )

        if situation.evidence_situation_ids:
            history_contribution = min(
                len(situation.evidence_situation_ids) / 5.0,
                1.0,
            )

            factors.append(
                self._factor(
                    "historical",
                    "historical_evidence",
                    str(
                        len(
                            situation.evidence_situation_ids
                        )
                    ),
                    history_contribution,
                    "Historical situation IDs support the prediction.",
                )
            )

        if "risk_forecast" in situation.prediction_sources:
            factors.append(
                self._factor(
                    "risk",
                    "risk_forecast",
                    "present",
                    0.80,
                    "A risk forecast contributes supporting evidence.",
                )
            )

        if "recurrence_prediction" in situation.prediction_sources:
            factors.append(
                self._factor(
                    "recurrence",
                    "recurrence_prediction",
                    "present",
                    0.80,
                    "A recurrence prediction contributes supporting evidence.",
                )
            )

        if "workload_forecast" in situation.prediction_sources:
            factors.append(
                self._factor(
                    "workload",
                    "workload_forecast",
                    "present",
                    0.80,
                    "A workload forecast contributes supporting evidence.",
                )
            )

        return factors

    @staticmethod
    def _evidence_strength(
        situation: PredictiveSituation,
        factors: Sequence[PredictionFactor],
    ) -> float:
        if not factors:
            return 0.0

        unique_types = len(
            {
                factor.factor_type
                for factor in factors
            }
        )

        source_count = len(
            situation.prediction_sources
        )

        historical_count = len(
            situation.evidence_situation_ids
        )

        strength = (
            0.35
            + min(unique_types / 6.0, 1.0) * 0.25
            + min(source_count / 4.0, 1.0) * 0.20
            + min(historical_count / 5.0, 1.0) * 0.20
        )

        return round(
            max(0.0, min(1.0, strength)),
            6,
        )

    @staticmethod
    def _build_explanation(
        situation: PredictiveSituation,
        factors: Sequence[PredictionFactor],
        evidence_strength: float,
        uncertainty: float,
    ) -> str:
        factor_names = ", ".join(
            factor.name
            for factor in factors
        )

        sources = ", ".join(
            situation.prediction_sources
        ) or "predictive signal"

        return (
            f"YOMA predicts a {situation.situation_type} situation "
            f"with probability {situation.probability:.2f} and "
            f"confidence {situation.confidence:.2f}. "
            f"Supporting sources are {sources}. "
            f"Contributing factors are {factor_names or 'limited evidence'}. "
            f"Evidence strength is {evidence_strength:.2f}, "
            f"with uncertainty {uncertainty:.2f}. "
            "This prediction is advisory and requires human review."
        )

    @staticmethod
    def _build_limitations(
        situation: PredictiveSituation,
        factors: Sequence[PredictionFactor],
    ) -> list[str]:
        limitations = [
            "Prediction is probabilistic and is not a certainty.",
            "Historical evidence may not represent future operating conditions.",
            "No autonomous action is authorized by this explanation.",
        ]

        if situation.confidence < 0.50:
            limitations.append(
                "Confidence is low; prediction should receive additional human scrutiny."
            )

        if not situation.evidence_situation_ids:
            limitations.append(
                "No historical situation IDs were supplied as direct evidence."
            )

        if len(situation.prediction_sources) <= 1:
            limitations.append(
                "Prediction is based on a limited number of predictive sources."
            )

        return limitations

    def explain_many(
        self,
        contexts: Sequence[PredictiveDecisionContext],
    ) -> tuple[PredictionExplainability, ...]:
        return tuple(
            self.explain(context)
            for context in contexts
        )
