from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.baseline_trend import BaselineTrend
from yoma.office.operations.situation import OperationalSituation


@dataclass(frozen=True)
class PredictiveSignal:
    """
    Deterministic advisory prediction derived from historical recurrence
    and baseline/trend intelligence.

    This object does not execute actions.
    """

    prediction_id: str
    prediction_type: str
    situation_type: str

    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]

    recurrence_likelihood: float
    confidence: float

    predicted_next_occurrence_start: Optional[datetime]
    predicted_next_occurrence_end: Optional[datetime]

    historical_occurrences: int
    baseline_daily_frequency: float
    recent_daily_frequency: float
    previous_daily_frequency: float

    trend_direction: str
    trend_ratio: float
    deviation_from_baseline: float

    average_recurrence_interval_seconds: Optional[float]

    historical_pattern_id: Optional[str]
    evidence_situation_ids: tuple[str, ...]

    evidence: tuple[str, ...]

    requires_human_approval: bool = True

    @property
    def elevated(self) -> bool:
        return self.recurrence_likelihood >= 0.60

    @property
    def historical_evidence_available(self) -> bool:
        return bool(
            self.historical_pattern_id
            or self.evidence_situation_ids
        )


class PredictiveSignalEngine:
    """
    Converts historical patterns and baseline/trend information into
    deterministic predictive signals.

    Design rules:
    - explicit scope matching only
    - no fuzzy/name inference
    - no persistence changes
    - no autonomous action
    - bounded likelihood/confidence values
    """

    def __init__(
        self,
        patterns: list[HistoricalPattern]
        | tuple[HistoricalPattern, ...],
        trends: list[BaselineTrend]
        | tuple[BaselineTrend, ...],
    ) -> None:
        for pattern in patterns:
            if not isinstance(pattern, HistoricalPattern):
                raise TypeError(
                    "patterns must contain HistoricalPattern objects"
                )

        for trend in trends:
            if not isinstance(trend, BaselineTrend):
                raise TypeError(
                    "trends must contain BaselineTrend objects"
                )

        self.patterns = tuple(patterns)
        self.trends = tuple(trends)

    def predict(
        self,
        situation: OperationalSituation,
    ) -> PredictiveSignal:
        if not isinstance(
            situation,
            OperationalSituation,
        ):
            raise TypeError(
                "situation must be OperationalSituation"
            )

        pattern = self._find_pattern(situation)
        trend = self._find_trend(situation)

        occurrence_count = (
            pattern.occurrence_count
            if pattern is not None
            else 0
        )

        pattern_id = (
            pattern.pattern_id
            if pattern is not None
            else None
        )

        evidence_ids = (
            pattern.situation_ids
            if pattern is not None
            else ()
        )

        average_interval = (
            pattern.average_recurrence_interval_seconds
            if pattern is not None
            else None
        )

        if trend is not None:
            baseline_frequency = trend.baseline_daily_frequency
            recent_frequency = trend.recent_daily_frequency
            previous_frequency = trend.previous_daily_frequency
            trend_direction = trend.trend_direction
            trend_ratio = trend.trend_ratio
            deviation = trend.deviation_from_baseline

            if average_interval is None:
                average_interval = (
                    trend.average_recurrence_interval_seconds
                )
        else:
            baseline_frequency = 0.0
            recent_frequency = 0.0
            previous_frequency = 0.0
            trend_direction = "unknown"
            trend_ratio = 1.0
            deviation = 0.0

        likelihood = self._likelihood(
            occurrence_count=occurrence_count,
            trend_direction=trend_direction,
            trend_ratio=trend_ratio,
            deviation=deviation,
            average_interval=average_interval,
        )

        confidence = self._confidence(
            occurrence_count=occurrence_count,
            has_trend=trend is not None,
            average_interval=average_interval,
        )

        next_start, next_end = self._next_occurrence_window(
            situation.detected_at,
            average_interval,
            likelihood,
        )

        prediction_id = self._prediction_id(
            situation=situation,
            pattern=pattern,
        )

        evidence = self._build_evidence(
            situation=situation,
            pattern=pattern,
            trend=trend,
            likelihood=likelihood,
            confidence=confidence,
        )

        return PredictiveSignal(
            prediction_id=prediction_id,
            prediction_type="recurrence_prediction",
            situation_type=situation.situation_type,
            organization_id=situation.organization_id,
            user_id=situation.user_id,
            system_id=situation.system_id,
            recurrence_likelihood=likelihood,
            confidence=confidence,
            predicted_next_occurrence_start=next_start,
            predicted_next_occurrence_end=next_end,
            historical_occurrences=occurrence_count,
            baseline_daily_frequency=baseline_frequency,
            recent_daily_frequency=recent_frequency,
            previous_daily_frequency=previous_frequency,
            trend_direction=trend_direction,
            trend_ratio=trend_ratio,
            deviation_from_baseline=deviation,
            average_recurrence_interval_seconds=average_interval,
            historical_pattern_id=pattern_id,
            evidence_situation_ids=evidence_ids,
            evidence=evidence,
            requires_human_approval=True,
        )

    def predict_many(
        self,
        situations: list[OperationalSituation]
        | tuple[OperationalSituation, ...],
    ) -> list[PredictiveSignal]:
        return [
            self.predict(situation)
            for situation in situations
        ]

    def _find_pattern(
        self,
        situation: OperationalSituation,
    ) -> Optional[HistoricalPattern]:
        matches = [
            pattern
            for pattern in self.patterns
            if self._scope_matches(
                situation.situation_type,
                situation.organization_id,
                situation.user_id,
                situation.system_id,
                pattern.situation_type,
                pattern.organization_id,
                pattern.user_id,
                pattern.system_id,
            )
        ]

        if not matches:
            return None

        return max(
            matches,
            key=lambda item: (
                item.occurrence_count,
                item.last_occurred_at,
                item.pattern_id,
            ),
        )

    def _find_trend(
        self,
        situation: OperationalSituation,
    ) -> Optional[BaselineTrend]:
        matches = [
            trend
            for trend in self.trends
            if self._scope_matches(
                situation.situation_type,
                situation.organization_id,
                situation.user_id,
                situation.system_id,
                trend.situation_type,
                trend.organization_id,
                trend.user_id,
                trend.system_id,
            )
        ]

        if not matches:
            return None

        return max(
            matches,
            key=lambda item: (
                item.total_occurrences,
                item.last_occurred_at,
                item.situation_type,
                item.organization_id or "",
                item.user_id or "",
                item.system_id or "",
            ),
        )

    @staticmethod
    def _scope_matches(
        situation_type: str,
        organization_id: Optional[str],
        user_id: Optional[str],
        system_id: Optional[str],
        candidate_type: str,
        candidate_organization: Optional[str],
        candidate_user: Optional[str],
        candidate_system: Optional[str],
    ) -> bool:
        return (
            situation_type == candidate_type
            and organization_id == candidate_organization
            and user_id == candidate_user
            and system_id == candidate_system
        )

    @staticmethod
    def _likelihood(
        *,
        occurrence_count: int,
        trend_direction: str,
        trend_ratio: float,
        deviation: float,
        average_interval: Optional[float],
    ) -> float:
        if occurrence_count <= 0:
            return 0.0

        # Recurrence evidence.
        recurrence_component = min(
            occurrence_count / 10.0,
            1.0,
        )

        # Recent trend evidence.
        if trend_direction == "increasing":
            trend_component = 0.80
        elif trend_direction == "stable":
            trend_component = 0.55
        elif trend_direction == "decreasing":
            trend_component = 0.25
        else:
            trend_component = 0.35

        # Stronger recent acceleration modestly increases likelihood.
        if trend_ratio != float("inf"):
            ratio_component = min(
                max(trend_ratio / 3.0, 0.0),
                1.0,
            )
        else:
            ratio_component = 1.0

        deviation_component = min(
            max((deviation + 1.0) / 2.0, 0.0),
            1.0,
        )

        # Regular recurrence gives additional evidence.
        interval_component = (
            0.65
            if average_interval is not None
            else 0.0
        )

        score = (
            0.35 * recurrence_component
            + 0.25 * trend_component
            + 0.15 * ratio_component
            + 0.15 * deviation_component
            + 0.10 * interval_component
        )

        return round(
            min(max(score, 0.0), 1.0),
            6,
        )

    @staticmethod
    def _confidence(
        *,
        occurrence_count: int,
        has_trend: bool,
        average_interval: Optional[float],
    ) -> float:
        evidence = min(
            occurrence_count / 5.0,
            1.0,
        )

        confidence = (
            0.55 * evidence
            + 0.25 * (1.0 if has_trend else 0.0)
            + 0.20 * (
                1.0
                if average_interval is not None
                else 0.0
            )
        )

        return round(
            min(max(confidence, 0.0), 1.0),
            6,
        )

    @staticmethod
    def _next_occurrence_window(
        detected_at: datetime,
        average_interval: Optional[float],
        likelihood: float,
    ) -> tuple[
        Optional[datetime],
        Optional[datetime],
    ]:
        if (
            average_interval is None
            or likelihood <= 0.0
        ):
            return None, None

        center = detected_at + timedelta(
            seconds=average_interval
        )

        # ?25% interval window.
        margin = max(
            average_interval * 0.25,
            1.0,
        )

        return (
            center - timedelta(seconds=margin),
            center + timedelta(seconds=margin),
        )

    @staticmethod
    def _prediction_id(
        *,
        situation: OperationalSituation,
        pattern: Optional[HistoricalPattern],
    ) -> str:
        pattern_id = (
            pattern.pattern_id
            if pattern is not None
            else "NO_PATTERN"
        )

        return (
            "PRED-"
            f"{situation.situation_type}-"
            f"{situation.organization_id or 'GLOBAL'}-"
            f"{situation.user_id or 'GLOBAL'}-"
            f"{situation.system_id or 'GLOBAL'}-"
            f"{pattern_id}-"
            f"{situation.situation_id}"
        )

    @staticmethod
    def _build_evidence(
        *,
        situation: OperationalSituation,
        pattern: Optional[HistoricalPattern],
        trend: Optional[BaselineTrend],
        likelihood: float,
        confidence: float,
    ) -> tuple[str, ...]:
        evidence: list[str] = []

        if pattern is not None:
            evidence.append(
                f"historical_pattern:{pattern.pattern_id}"
            )
            evidence.append(
                f"historical_occurrences:{pattern.occurrence_count}"
            )

        if trend is not None:
            evidence.append(
                f"trend_direction:{trend.trend_direction}"
            )
            evidence.append(
                f"trend_ratio:{trend.trend_ratio}"
            )
            evidence.append(
                f"baseline_deviation:{trend.deviation_from_baseline}"
            )

        evidence.append(
            f"recurrence_likelihood:{likelihood}"
        )
        evidence.append(
            f"prediction_confidence:{confidence}"
        )

        if not evidence:
            evidence.append(
                f"no_historical_evidence:{situation.situation_id}"
            )

        return tuple(evidence)


__all__ = [
    "PredictiveSignal",
    "PredictiveSignalEngine",
]
