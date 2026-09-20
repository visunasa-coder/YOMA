from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yoma.office.operations.situation import OperationalSituation
from yoma.office.historical_pattern import HistoricalPattern
from yoma.office.baseline_trend import BaselineTrend


@dataclass(frozen=True)
class HistoricalDecisionContext:
    """
    Historical evidence attached to an operational situation.

    This context is advisory only. It does not create or execute actions.
    """

    situation_id: str
    situation_type: str

    organization_id: Optional[str]
    user_id: Optional[str]
    system_id: Optional[str]

    occurrence_count: int
    historical_pattern_id: Optional[str]

    baseline_daily_frequency: float
    recent_daily_frequency: float
    previous_daily_frequency: float

    deviation_from_baseline: float
    frequency_change: float
    trend_ratio: float
    trend_direction: str

    average_recurrence_interval_seconds: Optional[float]

    historical_situation_ids: tuple[str, ...]

    evidence: tuple[str, ...]

    requires_human_approval: bool = True

    @property
    def recurring(self) -> bool:
        return self.occurrence_count >= 2

    @property
    def above_baseline(self) -> bool:
        return self.deviation_from_baseline > 0.0

    @property
    def below_baseline(self) -> bool:
        return self.deviation_from_baseline < 0.0

    @property
    def historical_context_available(self) -> bool:
        return bool(
            self.historical_pattern_id
            or self.historical_situation_ids
            or self.trend_direction != "unknown"
        )


class HistoricalDecisionContextBuilder:
    """
    Combines a current OperationalSituation with historical pattern and
    baseline/trend intelligence.

    Matching is based exclusively on explicit identity dimensions:
    situation_type + organization_id + user_id + system_id.

    No name inference or fuzzy matching is performed.
    """

    def __init__(
        self,
        patterns: list[HistoricalPattern] | tuple[HistoricalPattern, ...],
        trends: list[BaselineTrend] | tuple[BaselineTrend, ...],
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

    def build(
        self,
        situation: OperationalSituation,
    ) -> HistoricalDecisionContext:
        if not isinstance(situation, OperationalSituation):
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

        historical_ids = (
            pattern.situation_ids
            if pattern is not None
            else ()
        )

        if trend is not None:
            baseline_daily_frequency = (
                trend.baseline_daily_frequency
            )
            recent_daily_frequency = (
                trend.recent_daily_frequency
            )
            previous_daily_frequency = (
                trend.previous_daily_frequency
            )
            deviation_from_baseline = (
                trend.deviation_from_baseline
            )
            frequency_change = trend.frequency_change
            trend_ratio = trend.trend_ratio
            trend_direction = trend.trend_direction
            average_interval = (
                trend.average_recurrence_interval_seconds
            )
        else:
            baseline_daily_frequency = 0.0
            recent_daily_frequency = 0.0
            previous_daily_frequency = 0.0
            deviation_from_baseline = 0.0
            frequency_change = 0.0
            trend_ratio = 1.0
            trend_direction = "unknown"
            average_interval = None

        evidence = self._build_evidence(
            situation=situation,
            pattern=pattern,
            trend=trend,
        )

        return HistoricalDecisionContext(
            situation_id=situation.situation_id,
            situation_type=situation.situation_type,
            organization_id=situation.organization_id,
            user_id=situation.user_id,
            system_id=situation.system_id,
            occurrence_count=occurrence_count,
            historical_pattern_id=pattern_id,
            baseline_daily_frequency=baseline_daily_frequency,
            recent_daily_frequency=recent_daily_frequency,
            previous_daily_frequency=previous_daily_frequency,
            deviation_from_baseline=deviation_from_baseline,
            frequency_change=frequency_change,
            trend_ratio=trend_ratio,
            trend_direction=trend_direction,
            average_recurrence_interval_seconds=average_interval,
            historical_situation_ids=historical_ids,
            evidence=evidence,
            requires_human_approval=True,
        )

    def build_many(
        self,
        situations: list[OperationalSituation]
        | tuple[OperationalSituation, ...],
    ) -> list[HistoricalDecisionContext]:
        return [
            self.build(situation)
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
                situation_type=situation.situation_type,
                organization_id=situation.organization_id,
                user_id=situation.user_id,
                system_id=situation.system_id,
                candidate_type=pattern.situation_type,
                candidate_organization=pattern.organization_id,
                candidate_user=pattern.user_id,
                candidate_system=pattern.system_id,
            )
        ]

        if not matches:
            return None

        return max(
            matches,
            key=lambda pattern: (
                pattern.occurrence_count,
                pattern.last_occurred_at,
                pattern.pattern_id,
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
                situation_type=situation.situation_type,
                organization_id=situation.organization_id,
                user_id=situation.user_id,
                system_id=situation.system_id,
                candidate_type=trend.situation_type,
                candidate_organization=trend.organization_id,
                candidate_user=trend.user_id,
                candidate_system=trend.system_id,
            )
        ]

        if not matches:
            return None

        return max(
            matches,
            key=lambda trend: (
                trend.total_occurrences,
                trend.last_occurred_at,
                trend.situation_type,
                trend.organization_id or "",
                trend.user_id or "",
                trend.system_id or "",
            ),
        )

    @staticmethod
    def _scope_matches(
        *,
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
    def _build_evidence(
        *,
        situation: OperationalSituation,
        pattern: Optional[HistoricalPattern],
        trend: Optional[BaselineTrend],
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
                f"baseline_daily_frequency:{trend.baseline_daily_frequency}"
            )
            evidence.append(
                f"recent_daily_frequency:{trend.recent_daily_frequency}"
            )
            evidence.append(
                f"previous_daily_frequency:{trend.previous_daily_frequency}"
            )
            evidence.append(
                f"trend_direction:{trend.trend_direction}"
            )
            evidence.append(
                f"baseline_deviation:{trend.deviation_from_baseline}"
            )

        if not evidence:
            evidence.append(
                f"no_historical_match:{situation.situation_id}"
            )

        return tuple(evidence)


__all__ = [
    "HistoricalDecisionContext",
    "HistoricalDecisionContextBuilder",
]
