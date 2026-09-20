"""M29.5 predictive situation detection for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Sequence

from yoma.office.predictive_signal import PredictiveSignal
from yoma.office.risk_forecast import RiskForecast
from yoma.office.workload_forecast import WorkloadForecast
from yoma.office.recurrence_prediction import RecurrencePrediction


@dataclass(frozen=True)
class PredictiveSituation:
    """Advisory representation of a situation likely to emerge."""

    prediction_id: str
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]
    predicted_at: datetime
    forecast_start: Optional[datetime]
    forecast_end: Optional[datetime]
    probability: float
    confidence: float
    severity: str
    prediction_sources: tuple[str, ...]
    evidence_situation_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if (
            self.forecast_start is not None
            and self.forecast_end is not None
            and self.forecast_end < self.forecast_start
        ):
            raise ValueError(
                "forecast_end must not precede forecast_start"
            )

        allowed = {"info", "warning", "high", "critical"}
        if self.severity not in allowed:
            raise ValueError(
                "severity must be one of info, warning, high, critical"
            )

    @property
    def elevated(self) -> bool:
        return self.probability >= 0.60

    @property
    def detection_available(self) -> bool:
        return (
            self.forecast_start is not None
            and self.forecast_end is not None
        )

    @property
    def historical_evidence_available(self) -> bool:
        return bool(self.evidence_situation_ids)


class PredictiveSituationDetector:
    """
    Detects likely future operational situations from existing predictions.

    This class only composes existing predictive outputs. It does not
    persist predictions and does not execute operational actions.
    """

    def __init__(
        self,
        predictive_signals: Iterable[PredictiveSignal] = (),
        risk_forecasts: Iterable[RiskForecast] = (),
        recurrence_predictions: Iterable[RecurrencePrediction] = (),
        workload_forecasts: Iterable[WorkloadForecast] = (),
    ) -> None:
        self._signals = tuple(predictive_signals)
        self._risks = tuple(risk_forecasts)
        self._recurrences = tuple(recurrence_predictions)
        self._workloads = tuple(workload_forecasts)

    @staticmethod
    def _scope(
        item: object,
    ) -> tuple[
        Optional[str],
        Optional[str],
        Optional[str],
        str,
    ]:
        return (
            getattr(item, "organization_id"),
            getattr(item, "user_id"),
            getattr(item, "system_id"),
            getattr(item, "situation_type"),
        )

    @staticmethod
    def _severity(
        probability: float,
        risk_severity: Optional[str],
    ) -> str:
        if risk_severity in {"critical", "high"}:
            return risk_severity

        if probability >= 0.85:
            return "critical"

        if probability >= 0.65:
            return "high"

        if probability >= 0.40:
            return "warning"

        return "info"

    @staticmethod
    def _average(values: Sequence[float]) -> float:
        if not values:
            return 0.0

        return round(
            sum(values) / len(values),
            6,
        )

    @staticmethod
    def _first_available(
        *values: Optional[datetime],
    ) -> Optional[datetime]:
        for value in values:
            if value is not None:
                return value

        return None

    @staticmethod
    def _last_available(
        *values: Optional[datetime],
    ) -> Optional[datetime]:
        available = [
            value
            for value in values
            if value is not None
        ]

        return max(available) if available else None

    def _matching(
        self,
        source: Iterable[object],
        target: object,
    ) -> list[object]:
        target_scope = self._scope(target)

        return [
            item
            for item in source
            if self._scope(item) == target_scope
        ]

    def detect(
        self,
        predictive_signal: PredictiveSignal,
    ) -> PredictiveSituation:
        risks = self._matching(
            self._risks,
            predictive_signal,
        )

        recurrences = self._matching(
            self._recurrences,
            predictive_signal,
        )

        workloads = self._matching(
            self._workloads,
            predictive_signal,
        )

        risk = max(
            risks,
            key=lambda item: (
                item.risk_probability,
                item.confidence,
                item.forecast_id,
            ),
            default=None,
        )

        recurrence = max(
            recurrences,
            key=lambda item: (
                item.recurrence_probability,
                item.confidence,
                item.prediction_id,
            ),
            default=None,
        )

        workload = max(
            workloads,
            key=lambda item: (
                item.workload_probability,
                item.confidence,
                item.forecast_id,
            ),
            default=None,
        )

        probabilities = [
            predictive_signal.recurrence_likelihood,
        ]

        confidences = [
            predictive_signal.confidence,
        ]

        if risk is not None:
            probabilities.append(risk.risk_probability)
            confidences.append(risk.confidence)

        if recurrence is not None:
            probabilities.append(
                recurrence.recurrence_probability
            )
            confidences.append(recurrence.confidence)

        if workload is not None:
            probabilities.append(
                workload.workload_probability
            )
            confidences.append(workload.confidence)

        probability = self._average(probabilities)
        confidence = self._average(confidences)

        forecast_start = self._first_available(
            (
                risk.forecast_start
                if risk is not None
                else None
            ),
            (
                recurrence.predicted_next_occurrence_start
                if recurrence is not None
                else None
            ),
            (
                workload.forecast_start
                if workload is not None
                else None
            ),
            predictive_signal.predicted_next_occurrence_start,
        )

        forecast_end = self._last_available(
            (
                risk.forecast_end
                if risk is not None
                else None
            ),
            (
                recurrence.predicted_next_occurrence_end
                if recurrence is not None
                else None
            ),
            (
                workload.forecast_end
                if workload is not None
                else None
            ),
            predictive_signal.predicted_next_occurrence_end,
        )

        risk_severity = (
            risk.risk_severity
            if risk is not None
            else None
        )

        severity = self._severity(
            probability,
            risk_severity,
        )

        sources = ["predictive_signal"]

        if risk is not None:
            sources.append("risk_forecast")

        if recurrence is not None:
            sources.append("recurrence_prediction")

        if workload is not None:
            sources.append("workload_forecast")

        evidence_ids = list(
            predictive_signal.evidence_situation_ids
        )

        if recurrence is not None:
            evidence_ids.extend(
                recurrence.evidence_situation_ids
            )

        if workload is not None:
            evidence_ids.extend(
                workload.evidence_situation_ids
            )

        evidence_ids = list(
            dict.fromkeys(evidence_ids)
        )

        evidence = (
            f"prediction_probability={probability:.6f}",
            f"prediction_confidence={confidence:.6f}",
            f"prediction_sources={','.join(sources)}",
            f"risk_probability={getattr(risk, 'risk_probability', None)}",
            f"recurrence_probability={getattr(recurrence, 'recurrence_probability', None)}",
            f"workload_probability={getattr(workload, 'workload_probability', None)}",
            f"severity={severity}",
        )

        prediction_id = (
            f"PSIT-{predictive_signal.prediction_id}"
        )

        return PredictiveSituation(
            prediction_id=prediction_id,
            situation_type=predictive_signal.situation_type,
            organization_id=predictive_signal.organization_id,
            user_id=predictive_signal.user_id,
            system_id=predictive_signal.system_id,
            predicted_at=(
                predictive_signal.predicted_next_occurrence_start
                if predictive_signal.predicted_next_occurrence_start is not None
                else datetime.now()
            ),
            forecast_start=forecast_start,
            forecast_end=forecast_end,
            probability=probability,
            confidence=confidence,
            severity=severity,
            prediction_sources=tuple(sources),
            evidence_situation_ids=tuple(evidence_ids),
            evidence=evidence,
            requires_human_approval=True,
        )

    def detect_many(
        self,
        predictive_signals: Sequence[PredictiveSignal],
    ) -> tuple[PredictiveSituation, ...]:
        return tuple(
            self.detect(signal)
            for signal in predictive_signals
        )
