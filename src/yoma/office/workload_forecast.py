"""M29.4 workload and operational forecasting for YOMA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from yoma.office.baseline_trend import BaselineTrend
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.operations.situation import OperationalSituation


@dataclass(frozen=True)
class WorkloadForecast:
    """Deterministic advisory forecast of operational workload."""

    forecast_id: str
    forecast_type: str
    situation_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]
    forecast_start: Optional[datetime]
    forecast_end: Optional[datetime]
    baseline_daily_frequency: float
    forecast_daily_frequency: float
    recent_daily_frequency: float
    previous_daily_frequency: float
    frequency_change: float
    deviation_from_baseline: float
    trend_ratio: float
    trend_direction: str
    workload_probability: float
    confidence: float
    historical_occurrences: int
    historical_pattern_id: Optional[str]
    evidence_situation_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    requires_human_approval: bool = True

    def __post_init__(self) -> None:
        if self.baseline_daily_frequency < 0:
            raise ValueError(
                "baseline_daily_frequency must be non-negative"
            )

        if self.forecast_daily_frequency < 0:
            raise ValueError(
                "forecast_daily_frequency must be non-negative"
            )

        if self.recent_daily_frequency < 0:
            raise ValueError(
                "recent_daily_frequency must be non-negative"
            )

        if self.previous_daily_frequency < 0:
            raise ValueError(
                "previous_daily_frequency must be non-negative"
            )

        if not 0.0 <= self.workload_probability <= 1.0:
            raise ValueError(
                "workload_probability must be between 0 and 1"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if self.historical_occurrences < 0:
            raise ValueError(
                "historical_occurrences must be non-negative"
            )

        if (
            self.forecast_start is not None
            and self.forecast_end is not None
            and self.forecast_end < self.forecast_start
        ):
            raise ValueError(
                "forecast_end must not precede forecast_start"
            )

    @property
    def elevated(self) -> bool:
        return self.workload_probability >= 0.60

    @property
    def forecast_available(self) -> bool:
        return (
            self.forecast_start is not None
            and self.forecast_end is not None
        )

    @property
    def above_baseline(self) -> bool:
        return self.forecast_daily_frequency > (
            self.baseline_daily_frequency
        )


class WorkloadForecastEngine:
    """
    Converts historical baseline/trend evidence into a workload forecast.

    The forecast is deterministic, bounded, and advisory only.
    """

    def __init__(
        self,
        patterns: Iterable[HistoricalPattern] = (),
        trends: Iterable[BaselineTrend] = (),
        *,
        forecast_days: int = 7,
    ) -> None:
        if forecast_days <= 0:
            raise ValueError("forecast_days must be positive")

        self._patterns = tuple(patterns)
        self._trends = tuple(trends)
        self._forecast_days = forecast_days

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
    def _forecast_frequency(
        trend: Optional[BaselineTrend],
    ) -> float:
        if trend is None:
            return 0.0

        # Project the recent frequency using the observed recent-vs-previous
        # change. Never produce a negative workload frequency.
        projected = (
            trend.recent_daily_frequency
            + trend.frequency_change
        )

        return round(max(0.0, projected), 6)

    @staticmethod
    def _probability(
        *,
        historical_occurrences: int,
        trend: Optional[BaselineTrend],
        forecast_frequency: float,
    ) -> float:
        if trend is None and historical_occurrences <= 1:
            return 0.20

        occurrence_factor = min(
            historical_occurrences / 10.0,
            1.0,
        )

        score = 0.20 + (0.30 * occurrence_factor)

        if trend is not None:
            if trend.trend_direction == "increasing":
                score += 0.20
            elif trend.trend_direction == "decreasing":
                score += 0.05
            else:
                score += 0.10

            if (
                trend.baseline_daily_frequency > 0
                and forecast_frequency
                > trend.baseline_daily_frequency
            ):
                score += 0.15

            score += 0.10 * min(
                abs(trend.deviation_from_baseline),
                1.0,
            )

        return round(
            max(0.0, min(1.0, score)),
            6,
        )

    @staticmethod
    def _confidence(
        *,
        historical_occurrences: int,
        trend_available: bool,
    ) -> float:
        confidence = (
            0.25
            + min(historical_occurrences, 10) * 0.045
        )

        if trend_available:
            confidence += 0.20

        return round(
            max(0.0, min(1.0, confidence)),
            6,
        )

    def forecast(
        self,
        situation: OperationalSituation,
    ) -> WorkloadForecast:
        pattern = self._best_pattern(situation)
        trend = self._best_trend(situation)

        historical_occurrences = (
            pattern.occurrence_count
            if pattern is not None
            else 1
        )

        baseline = (
            trend.baseline_daily_frequency
            if trend is not None
            else 0.0
        )

        recent = (
            trend.recent_daily_frequency
            if trend is not None
            else 0.0
        )

        previous = (
            trend.previous_daily_frequency
            if trend is not None
            else 0.0
        )

        frequency_change = (
            trend.frequency_change
            if trend is not None
            else 0.0
        )

        deviation = (
            trend.deviation_from_baseline
            if trend is not None
            else 0.0
        )

        trend_ratio = (
            trend.trend_ratio
            if trend is not None
            else 1.0
        )

        trend_direction = (
            trend.trend_direction
            if trend is not None
            else "unknown"
        )

        forecast_frequency = self._forecast_frequency(
            trend
        )

        probability = self._probability(
            historical_occurrences=historical_occurrences,
            trend=trend,
            forecast_frequency=forecast_frequency,
        )

        confidence = self._confidence(
            historical_occurrences=historical_occurrences,
            trend_available=trend is not None,
        )

        forecast_start = situation.detected_at
        forecast_end = (
            forecast_start
            + timedelta(days=self._forecast_days)
        )

        if pattern is not None:
            evidence_situation_ids = tuple(
                pattern.situation_ids
            )
            historical_pattern_id = pattern.pattern_id
        else:
            evidence_situation_ids = ()
            historical_pattern_id = None

        evidence = (
            f"historical_occurrences={historical_occurrences}",
            f"baseline_daily_frequency={baseline:.6f}",
            f"recent_daily_frequency={recent:.6f}",
            f"previous_daily_frequency={previous:.6f}",
            f"forecast_daily_frequency={forecast_frequency:.6f}",
            f"frequency_change={frequency_change:.6f}",
            f"deviation_from_baseline={deviation:.6f}",
            f"trend_ratio={trend_ratio:.6f}",
            f"trend_direction={trend_direction}",
        )

        forecast_id = (
            f"WLF-{situation.situation_type}-"
            f"{situation.organization_id or 'GLOBAL'}-"
            f"{situation.user_id or 'GLOBAL'}-"
            f"{situation.system_id or 'GLOBAL'}-"
            f"{historical_pattern_id or situation.situation_id}-"
            f"{situation.situation_id}"
        )

        return WorkloadForecast(
            forecast_id=forecast_id,
            forecast_type="workload_forecast",
            situation_type=situation.situation_type,
            organization_id=situation.organization_id,
            user_id=situation.user_id,
            system_id=situation.system_id,
            forecast_start=forecast_start,
            forecast_end=forecast_end,
            baseline_daily_frequency=baseline,
            forecast_daily_frequency=forecast_frequency,
            recent_daily_frequency=recent,
            previous_daily_frequency=previous,
            frequency_change=frequency_change,
            deviation_from_baseline=deviation,
            trend_ratio=trend_ratio,
            trend_direction=trend_direction,
            workload_probability=probability,
            confidence=confidence,
            historical_occurrences=historical_occurrences,
            historical_pattern_id=historical_pattern_id,
            evidence_situation_ids=evidence_situation_ids,
            evidence=evidence,
            requires_human_approval=True,
        )

    def forecast_many(
        self,
        situations: Sequence[OperationalSituation],
    ) -> tuple[WorkloadForecast, ...]:
        return tuple(
            self.forecast(situation)
            for situation in situations
        )
