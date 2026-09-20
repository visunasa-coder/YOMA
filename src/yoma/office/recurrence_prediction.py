"""M29.3 recurrence prediction for YOMA operational intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.operations.situation import OperationalSituation


@dataclass(frozen=True)
class RecurrencePrediction:
    """Deterministic, advisory prediction of a possible recurring situation."""

    prediction_id: str
    prediction_type: str
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]
    recurrence_probability: float
    confidence: float
    predicted_next_occurrence_start: Optional[datetime]
    predicted_next_occurrence_end: Optional[datetime]
    recurrence_interval_seconds: Optional[float]
    historical_occurrences: int
    trend_direction: str
    trend_ratio: float
    deviation_from_baseline: float
    historical_pattern_id: Optional[str]
    evidence_situation_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.recurrence_probability <= 1.0:
            raise ValueError("recurrence_probability must be between 0 and 1")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if self.historical_occurrences < 0:
            raise ValueError("historical_occurrences must be non-negative")

        if (
            self.recurrence_interval_seconds is not None
            and self.recurrence_interval_seconds <= 0
        ):
            raise ValueError("recurrence_interval_seconds must be positive")

        if (
            self.predicted_next_occurrence_start is not None
            and self.predicted_next_occurrence_end is not None
            and self.predicted_next_occurrence_end
            < self.predicted_next_occurrence_start
        ):
            raise ValueError(
                "prediction end must not precede prediction start"
            )

    @property
    def elevated(self) -> bool:
        return self.recurrence_probability >= 0.60

    @property
    def prediction_available(self) -> bool:
        return (
            self.predicted_next_occurrence_start is not None
            and self.predicted_next_occurrence_end is not None
        )

    @property
    def historical_evidence_available(self) -> bool:
        return self.historical_occurrences >= 2


class RecurrencePredictionEngine:
    """
    Converts historical recurrence evidence into an advisory forecast.

    This engine does not persist data and never executes actions.
    """

    def __init__(
        self,
        patterns: Iterable[HistoricalPattern] = (),
        trends: Iterable[BaselineTrend] = (),
        *,
        window_fraction: float = 0.25,
    ) -> None:
        if not 0.0 < window_fraction <= 0.50:
            raise ValueError(
                "window_fraction must be > 0 and <= 0.50"
            )

        self._patterns = tuple(patterns)
        self._trends = tuple(trends)
        self._window_fraction = window_fraction

    @staticmethod
    def _scope_matches(
        situation: OperationalSituation,
        pattern: HistoricalPattern,
    ) -> bool:
        return (
            pattern.situation_type == situation.situation_type
            and pattern.organization_id == situation.organization_id
            and pattern.user_id == situation.user_id
            and pattern.system_id == situation.system_id
        )

    @staticmethod
    def _trend_matches(
        situation: OperationalSituation,
        trend: BaselineTrend,
    ) -> bool:
        return (
            trend.situation_type == situation.situation_type
            and trend.organization_id == situation.organization_id
            and trend.user_id == situation.user_id
            and trend.system_id == situation.system_id
        )

    def _best_pattern(
        self,
        situation: OperationalSituation,
    ) -> Optional[HistoricalPattern]:
        matches = [
            pattern
            for pattern in self._patterns
            if self._scope_matches(situation, pattern)
        ]

        return max(
            matches,
            key=lambda pattern: (
                pattern.occurrence_count,
                pattern.last_occurred_at,
                pattern.pattern_id,
            ),
            default=None,
        )

    def _best_trend(
        self,
        situation: OperationalSituation,
    ) -> Optional[BaselineTrend]:
        matches = [
            trend
            for trend in self._trends
            if self._trend_matches(situation, trend)
        ]

        return max(
            matches,
            key=lambda trend: (
                trend.total_occurrences,
                trend.last_occurred_at,
                trend.situation_type,
            ),
            default=None,
        )

    @staticmethod
    def _probability(
        *,
        occurrences: int,
        trend_direction: str,
        trend_ratio: float,
        deviation: float,
        interval_available: bool,
    ) -> float:
        """
        Conservative recurrence probability.

        Historical volume contributes most strongly, while trend and
        recurrence-interval evidence provide bounded adjustments.
        """

        occurrence_factor = min(occurrences / 10.0, 1.0)

        score = 0.20 + (0.35 * occurrence_factor)

        if interval_available:
            score += 0.15

        if trend_direction == "increasing":
            score += 0.15 * min(
                max(trend_ratio - 1.0, 0.0),
                1.0,
            )
        elif trend_direction == "decreasing":
            score -= 0.10 * min(
                max(1.0 - trend_ratio, 0.0),
                1.0,
            )

        score += 0.10 * min(
            max(abs(deviation), 0.0),
            1.0,
        )

        return round(
            max(0.0, min(1.0, score)),
            6,
        )

    @staticmethod
    def _confidence(
        *,
        occurrences: int,
        trend_available: bool,
        interval_available: bool,
    ) -> float:
        confidence = 0.25 + min(occurrences, 10) * 0.045

        if trend_available:
            confidence += 0.10

        if interval_available:
            confidence += 0.15

        return round(
            max(0.0, min(1.0, confidence)),
            6,
        )

    def predict(
        self,
        situation: OperationalSituation,
    ) -> RecurrencePrediction:
        pattern = self._best_pattern(situation)
        trend = self._best_trend(situation)

        interval = (
            pattern.average_recurrence_interval_seconds
            if pattern is not None
            else None
        )

        occurrences = (
            pattern.occurrence_count
            if pattern is not None
            else 1
        )

        trend_direction = (
            trend.trend_direction
            if trend is not None
            else "unknown"
        )

        trend_ratio = (
            trend.trend_ratio
            if trend is not None
            else 1.0
        )

        deviation = (
            trend.deviation_from_baseline
            if trend is not None
            else 0.0
        )

        probability = self._probability(
            occurrences=occurrences,
            trend_direction=trend_direction,
            trend_ratio=trend_ratio,
            deviation=deviation,
            interval_available=interval is not None,
        )

        confidence = self._confidence(
            occurrences=occurrences,
            trend_available=trend is not None,
            interval_available=interval is not None,
        )

        predicted_start: Optional[datetime] = None
        predicted_end: Optional[datetime] = None

        if interval is not None and interval > 0:
            expected = (
                situation.detected_at
                + timedelta(seconds=interval)
            )

            window = interval * self._window_fraction

            predicted_start = (
                expected - timedelta(seconds=window)
            )

            predicted_end = (
                expected + timedelta(seconds=window)
            )

        if pattern is not None:
            evidence_situation_ids = tuple(
                pattern.situation_ids
            )
            historical_pattern_id = pattern.pattern_id
        else:
            evidence_situation_ids = (
                situation.situation_id,
            )
            historical_pattern_id = None

        evidence = (
            f"historical_occurrences={occurrences}",
            f"trend_direction={trend_direction}",
            f"trend_ratio={trend_ratio:.6f}",
            f"deviation_from_baseline={deviation:.6f}",
            f"recurrence_interval_seconds={interval}",
        )

        prediction_id = (
            f"REC-{situation.situation_type}-"
            f"{situation.organization_id or 'GLOBAL'}-"
            f"{situation.user_id or 'GLOBAL'}-"
            f"{situation.system_id or 'GLOBAL'}-"
            f"{historical_pattern_id or 'GLOBAL'}-{situation.situation_id}"
        )

        return RecurrencePrediction(
            prediction_id=prediction_id,
            prediction_type="recurrence_prediction",
            situation_type=situation.situation_type,
            organization_id=situation.organization_id,
            user_id=situation.user_id,
            system_id=situation.system_id,
            recurrence_probability=probability,
            confidence=confidence,
            predicted_next_occurrence_start=predicted_start,
            predicted_next_occurrence_end=predicted_end,
            recurrence_interval_seconds=interval,
            historical_occurrences=occurrences,
            trend_direction=trend_direction,
            trend_ratio=trend_ratio,
            deviation_from_baseline=deviation,
            historical_pattern_id=historical_pattern_id,
            evidence_situation_ids=evidence_situation_ids,
            evidence=evidence,
            requires_human_approval=True,
        )

    def predict_many(
        self,
        situations: Sequence[OperationalSituation],
    ) -> tuple[RecurrencePrediction, ...]:
        return tuple(
            self.predict(situation)
            for situation in situations
        )
