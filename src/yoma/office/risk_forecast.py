from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from yoma.office.predictive_signal import PredictiveSignal


@dataclass(frozen=True)
class RiskForecast:
    """
    Deterministic advisory operational-risk forecast.

    A RiskForecast describes the expected operational risk represented by
    a PredictiveSignal. It does not execute actions.
    """

    forecast_id: str
    forecast_type: str
    situation_type: str

    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]

    risk_probability: float
    confidence: float
    risk_severity: str

    forecast_start: Optional[datetime]
    forecast_end: Optional[datetime]

    trend_direction: str
    trend_ratio: float
    baseline_deviation: float

    historical_occurrences: int
    historical_pattern_id: Optional[str]
    evidence_situation_ids: tuple[str, ...]

    evidence: tuple[str, ...]

    requires_human_approval: bool = True

    @property
    def elevated(self) -> bool:
        return self.risk_probability >= 0.60

    @property
    def high_risk(self) -> bool:
        return self.risk_severity in {
            "high",
            "critical",
        }

    @property
    def forecast_available(self) -> bool:
        return (
            self.forecast_start is not None
            and self.forecast_end is not None
        )


class RiskForecaster:
    """
    Converts M29.1 PredictiveSignal objects into operational-risk forecasts.

    The transformation is deterministic and advisory-only.
    """

    def forecast(
        self,
        prediction: PredictiveSignal,
    ) -> RiskForecast:
        if not isinstance(
            prediction,
            PredictiveSignal,
        ):
            raise TypeError(
                "prediction must be PredictiveSignal"
            )

        probability = self._risk_probability(
            prediction
        )

        severity = self._risk_severity(
            probability
        )

        forecast_id = self._forecast_id(
            prediction
        )

        evidence = self._build_evidence(
            prediction,
            probability,
            severity,
        )

        return RiskForecast(
            forecast_id=forecast_id,
            forecast_type="operational_risk_forecast",
            situation_type=prediction.situation_type,
            organization_id=prediction.organization_id,
            user_id=prediction.user_id,
            system_id=prediction.system_id,
            risk_probability=probability,
            confidence=prediction.confidence,
            risk_severity=severity,
            forecast_start=prediction.predicted_next_occurrence_start,
            forecast_end=prediction.predicted_next_occurrence_end,
            trend_direction=prediction.trend_direction,
            trend_ratio=prediction.trend_ratio,
            baseline_deviation=prediction.deviation_from_baseline,
            historical_occurrences=prediction.historical_occurrences,
            historical_pattern_id=prediction.historical_pattern_id,
            evidence_situation_ids=prediction.evidence_situation_ids,
            evidence=evidence,
            requires_human_approval=True,
        )

    def forecast_many(
        self,
        predictions: list[PredictiveSignal]
        | tuple[PredictiveSignal, ...],
    ) -> list[RiskForecast]:
        return [
            self.forecast(prediction)
            for prediction in predictions
        ]

    @staticmethod
    def _risk_probability(
        prediction: PredictiveSignal,
    ) -> float:
        """
        Risk probability combines recurrence likelihood with prediction
        confidence.

        Confidence acts as an evidence-quality multiplier rather than
        independently creating risk.
        """

        probability = (
            prediction.recurrence_likelihood
            * (
                0.50
                + 0.50 * prediction.confidence
            )
        )

        return round(
            min(max(probability, 0.0), 1.0),
            6,
        )

    @staticmethod
    def _risk_severity(
        probability: float,
    ) -> str:
        if probability >= 0.85:
            return "critical"

        if probability >= 0.65:
            return "high"

        if probability >= 0.40:
            return "warning"

        return "info"

    @staticmethod
    def _forecast_id(
        prediction: PredictiveSignal,
    ) -> str:
        return (
            "RISK-"
            f"{prediction.prediction_id}"
        )

    @staticmethod
    def _build_evidence(
        prediction: PredictiveSignal,
        probability: float,
        severity: str,
    ) -> tuple[str, ...]:
        evidence = list(
            prediction.evidence
        )

        evidence.append(
            f"risk_probability:{probability}"
        )
        evidence.append(
            f"risk_severity:{severity}"
        )

        return tuple(evidence)


__all__ = [
    "RiskForecast",
    "RiskForecaster",
]
